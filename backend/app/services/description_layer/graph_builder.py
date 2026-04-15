from __future__ import annotations

import json
import logging
import re
from typing import Any

from langgraph.graph import END, StateGraph

from .prompts import build_description_prompt
from .schemas import (
    AnalystDescriptionDraft,
    DescriptionGraphState,
    DescriptionPipelineOutput,
    IncidentPayload,
    PromptContext,
    TemplateExplanationItem,
)

logger = logging.getLogger(__name__)


class DescriptionGraphNodes:
    """Node implementations for LangGraph description enrichment workflow."""

    def __init__(self, llm: Any | None) -> None:
        self.llm = llm
        self._structured_chain = None
        if self.llm is not None:
            try:
                self._structured_chain = (
                    build_description_prompt()
                    | self.llm.with_structured_output(AnalystDescriptionDraft)
                )
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.exception("Failed to initialize structured LLM chain")
                self._structured_chain = None
                self.llm = None

    def ingest_input(self, state: DescriptionGraphState) -> DescriptionGraphState:
        """Stage: ingest_input."""

        payload = state.get("input_payload", {})
        if not isinstance(payload, dict):
            return {
                "input_payload": {},
                "errors": ["input_payload must be a dictionary"],
                "used_fallback": True,
            }

        return {
            "input_payload": payload,
            "errors": list(state.get("errors", [])),
            "used_fallback": bool(state.get("used_fallback", False)),
        }

    def validate_payload(self, state: DescriptionGraphState) -> DescriptionGraphState:
        """Stage: validate_payload."""

        payload = state.get("input_payload", {})
        try:
            incident = IncidentPayload.model_validate(payload)
            return {"incident": incident}
        except Exception as exc:
            logger.warning("Payload validation failed; using fallback path: %s", str(exc))
            errors = list(state.get("errors", []))
            errors.append(f"validate_payload failed: {exc}")
            return {"errors": errors, "used_fallback": True}

    def build_prompt_context(self, state: DescriptionGraphState) -> DescriptionGraphState:
        """Stage: build_prompt_context."""

        incident = state.get("incident")
        if incident is None:
            errors = list(state.get("errors", []))
            errors.append("build_prompt_context skipped because incident is unavailable")
            return {"errors": errors}

        positive_evidence = (
            incident.llm_input_ready.positive_evidence
            or _explanations_to_lines(incident.risk.template_explanations_positive)
        )
        negative_evidence = (
            incident.llm_input_ready.negative_evidence
            or _explanations_to_lines(incident.risk.template_explanations_negative)
        )

        prompt_context = PromptContext(
            incident_id=incident.incident_id,
            alert_id=incident.alert_id,
            source=incident.source,
            timestamp=incident.timestamp,
            summary=incident.summary or "",
            risk_score=incident.risk.risk_score,
            risk_label=incident.risk.risk_label,
            confidence_score=incident.risk.confidence_score,
            detection_label=incident.detection.detection_label,
            template_summary=(
                incident.narrative.template_summary
                or incident.llm_input_ready.template_summary
                or incident.summary
                or ""
            ),
            attack_type=incident.attack_assessment.likely_attack_type,
            attack_stage=incident.attack_assessment.likely_attack_stage,
            attack_reasoning=incident.attack_assessment.attack_reasoning,
            analyst_recommendation=(
                incident.narrative.analyst_recommendation
                or incident.llm_input_ready.analyst_recommendation
                or ""
            ),
            top_risk_factors=incident.risk.top_risk_factors,
            reducing_factors=incident.risk.risk_reducing_factors,
            positive_evidence=positive_evidence,
            negative_evidence=negative_evidence,
        )

        return {"prompt_context": prompt_context}

    def generate_description(self, state: DescriptionGraphState) -> DescriptionGraphState:
        """Stage: generate_description."""

        prompt_context = state.get("prompt_context")
        if prompt_context is None:
            errors = list(state.get("errors", []))
            errors.append("generate_description skipped because prompt context is unavailable")
            return {"errors": errors, "used_fallback": True}

        if self._structured_chain is None:
            errors = list(state.get("errors", []))
            errors.append("LLM chain is unavailable; fallback will be used")
            return {"errors": errors, "used_fallback": True}

        try:
            result = self._structured_chain.invoke(
                {
                    "prompt_context_json": json.dumps(
                        prompt_context.model_dump(), indent=2, ensure_ascii=True
                    )
                }
            )
            if isinstance(result, AnalystDescriptionDraft):
                return {"llm_result": result}
            return {"llm_result": AnalystDescriptionDraft.model_validate(result)}
        except Exception as exc:
            logger.warning("LLM description generation failed: %s", str(exc))
            errors = list(state.get("errors", []))
            errors.append(f"generate_description failed: {exc}")
            return {"errors": errors, "used_fallback": True}

    def validate_description(self, state: DescriptionGraphState) -> DescriptionGraphState:
        """Stage: validate_description."""

        llm_result = state.get("llm_result")
        prompt_context = state.get("prompt_context")
        if llm_result is None or prompt_context is None:
            errors = list(state.get("errors", []))
            errors.append("validate_description skipped because llm_result is unavailable")
            return {"errors": errors, "used_fallback": True}

        description = _normalize_text(llm_result.generated_description)
        validation_errors: list[str] = []

        sentence_count = _sentence_count(description)
        if sentence_count < 4 or sentence_count > 6:
            validation_errors.append(
                f"Description must contain 4-6 sentences; got {sentence_count}"
            )

        lowered_description = description.lower()
        if (
            prompt_context.attack_type
            and prompt_context.attack_type.lower() not in lowered_description
        ):
            validation_errors.append("Description does not mention attack_type")

        if (
            prompt_context.attack_stage
            and prompt_context.attack_stage.lower() not in lowered_description
        ):
            validation_errors.append("Description does not mention attack_stage")

        if prompt_context.top_risk_factors:
            factor_hits = sum(
                1
                for factor in prompt_context.top_risk_factors
                if factor.replace("_", " ").lower() in lowered_description
            )
            if factor_hits == 0:
                validation_errors.append(
                    "Description does not mention strongest risk drivers"
                )

        if prompt_context.reducing_factors:
            moderation_tokens = (
                "reduc",
                "moderat",
                "offset",
                "lower",
                "however",
                "but",
            )
            if not any(token in lowered_description for token in moderation_tokens):
                validation_errors.append(
                    "Description does not mention reducing/moderating signals"
                )

        if validation_errors:
            errors = list(state.get("errors", []))
            errors.extend(validation_errors)
            return {"errors": errors, "used_fallback": True}

        return {"generated_description": description}

    def fallback_if_needed(self, state: DescriptionGraphState) -> DescriptionGraphState:
        """Stage: fallback_if_needed."""

        if state.get("generated_description") and not state.get("errors"):
            return {"used_fallback": False}

        fallback_text = _extract_from_payload(
            state.get("input_payload", {}), ["narrative", "final_narrative"]
        )
        if not isinstance(fallback_text, str) or not fallback_text.strip():
            fallback_text = "Deterministic narrative unavailable from payload."

        return {
            "generated_description": _normalize_text(fallback_text),
            "used_fallback": True,
        }

    def format_final_output(self, state: DescriptionGraphState) -> DescriptionGraphState:
        """Stage: format_final_output."""

        incident = state.get("incident")
        payload = state.get("input_payload", {})

        if incident is not None:
            output = DescriptionPipelineOutput(
                incident_id=incident.incident_id,
                alert_id=incident.alert_id,
                risk_score=incident.risk.risk_score,
                risk_label=incident.risk.risk_label,
                template_summary=incident.narrative.template_summary,
                attack_type=incident.attack_assessment.likely_attack_type,
                attack_stage=incident.attack_assessment.likely_attack_stage,
                analyst_recommendation=incident.narrative.analyst_recommendation,
                generated_description=state.get("generated_description", ""),
                used_fallback=bool(state.get("used_fallback", False)),
            )
            return {"output": output}

        output = DescriptionPipelineOutput(
            incident_id=str(_extract_from_payload(payload, ["incident_id"], "unknown")),
            alert_id=str(_extract_from_payload(payload, ["alert_id"], "unknown")),
            risk_score=float(
                _extract_from_payload(payload, ["risk", "risk_score"], 0.0) or 0.0
            ),
            risk_label=str(_extract_from_payload(payload, ["risk", "risk_label"], "unknown")),
            template_summary=str(
                _extract_from_payload(payload, ["narrative", "template_summary"], "")
            ),
            attack_type=str(
                _extract_from_payload(
                    payload,
                    ["attack_assessment", "likely_attack_type"],
                    "unknown",
                )
            ),
            attack_stage=str(
                _extract_from_payload(
                    payload,
                    ["attack_assessment", "likely_attack_stage"],
                    "unknown",
                )
            ),
            analyst_recommendation=str(
                _extract_from_payload(
                    payload,
                    ["narrative", "analyst_recommendation"],
                    "",
                )
            ),
            generated_description=state.get("generated_description", ""),
            used_fallback=bool(state.get("used_fallback", True)),
        )
        return {"output": output}


def build_description_graph(llm: Any | None):
    """Build and compile the LangGraph workflow for description enrichment."""

    nodes = DescriptionGraphNodes(llm=llm)

    graph = StateGraph(DescriptionGraphState)

    graph.add_node("ingest_input", nodes.ingest_input)
    graph.add_node("validate_payload", nodes.validate_payload)
    graph.add_node("build_prompt_context", nodes.build_prompt_context)
    graph.add_node("generate_description", nodes.generate_description)
    graph.add_node("validate_description", nodes.validate_description)
    graph.add_node("fallback_if_needed", nodes.fallback_if_needed)
    graph.add_node("format_final_output", nodes.format_final_output)

    graph.set_entry_point("ingest_input")
    graph.add_edge("ingest_input", "validate_payload")
    graph.add_edge("validate_payload", "build_prompt_context")
    graph.add_edge("build_prompt_context", "generate_description")
    graph.add_edge("generate_description", "validate_description")
    graph.add_edge("validate_description", "fallback_if_needed")
    graph.add_edge("fallback_if_needed", "format_final_output")
    graph.add_edge("format_final_output", END)

    return graph.compile()


def _explanations_to_lines(items: list[TemplateExplanationItem]) -> list[str]:
    lines: list[str] = []
    for item in items:
        lines.append(
            (
                f"{item.feature}: {item.template} "
                f"(feature_value={item.feature_value}, shap_value={item.shap_value}, impact={item.impact})"
            )
        )
    return lines


def _extract_from_payload(
    payload: dict[str, Any], path: list[str], default: Any = ""
) -> Any:
    cursor: Any = payload
    for key in path:
        if not isinstance(cursor, dict) or key not in cursor:
            return default
        cursor = cursor[key]
    return cursor


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _sentence_count(text: str) -> int:
    if not text.strip():
        return 0
    sentence_parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return len([part for part in sentence_parts if part])
