from __future__ import annotations

import logging
import os
from typing import Any, Literal

from pydantic import BaseModel, Field

from .graph_builder import build_description_graph
from .schemas import DescriptionPipelineOutput

logger = logging.getLogger(__name__)


class LLMConfig(BaseModel):
    """Runtime configuration for LLM backend selection."""

    provider: Literal["openai", "ollama"] = Field(default="ollama")
    model_name: str | None = None
    temperature: float = 0.0
    timeout_seconds: int = 30
    api_key: str | None = None
    base_url: str | None = None


def create_chat_model(config: LLMConfig | None = None) -> Any:
    """Create a LangChain chat model for OpenAI or Ollama providers.

    This function abstracts provider creation so the rest of the service remains
    provider-agnostic.
    """

    cfg = config or LLMConfig()

    if cfg.provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except Exception as exc:  # pragma: no cover - import guard
            raise RuntimeError(
                "langchain-openai is required for provider='openai'."
            ) from exc

        api_key = cfg.api_key or os.getenv("OPENAI_API_KEY")
        model_name = cfg.model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for provider='openai'.")

        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=cfg.base_url,
            temperature=cfg.temperature,
            timeout=cfg.timeout_seconds,
        )

    if cfg.provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except Exception as exc:  # pragma: no cover - import guard
            raise RuntimeError(
                "langchain-ollama is required for provider='ollama'."
            ) from exc

        model_name = cfg.model_name or os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        base_url = cfg.base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        return ChatOllama(
            model=model_name,
            base_url=base_url,
            temperature=cfg.temperature,
        )

    raise RuntimeError(f"Unsupported LLM provider: {cfg.provider}")


class AnalystDescriptionService:
    """Service wrapper around LangGraph workflow for analyst description enrichment."""

    def __init__(
        self,
        llm: Any | None = None,
        llm_config: LLMConfig | None = None,
    ) -> None:
        self.llm = llm

        if self.llm is None:
            try:
                self.llm = create_chat_model(llm_config)
            except Exception as exc:
                # Non-fatal: service can still run deterministic fallback mode.
                logger.warning(
                    "LLM initialization failed. Service will use fallback narrative. Error: %s",
                    str(exc),
                )
                self.llm = None

        self.graph = build_description_graph(self.llm)

    def enrich_description(self, incident_payload: dict[str, Any]) -> dict[str, Any]:
        """Enrich incident output with analyst-grade description.

        The scoring output fields remain unchanged and are sourced directly from
        deterministic pipeline JSON.
        """

        try:
            state = self.graph.invoke({"input_payload": incident_payload})
            output = state.get("output")

            if isinstance(output, DescriptionPipelineOutput):
                return output.model_dump()

            if isinstance(output, dict):
                return DescriptionPipelineOutput.model_validate(output).model_dump()

            raise RuntimeError("LangGraph workflow returned no 'output' object.")
        except Exception as exc:
            logger.exception("Description enrichment failed. Returning safe fallback output.")
            return self._fallback_output(incident_payload, error_message=str(exc))

    def _fallback_output(
        self, incident_payload: dict[str, Any], error_message: str
    ) -> dict[str, Any]:
        """Build deterministic fallback response when workflow fails unexpectedly."""

        logger.warning("Fallback output used due to: %s", error_message)

        risk_section = incident_payload.get("risk", {})
        narrative_section = incident_payload.get("narrative", {})
        attack_section = incident_payload.get("attack_assessment", {})

        output = DescriptionPipelineOutput(
            incident_id=str(incident_payload.get("incident_id", "unknown")),
            alert_id=str(incident_payload.get("alert_id", "unknown")),
            risk_score=float(risk_section.get("risk_score", 0.0) or 0.0),
            risk_label=str(risk_section.get("risk_label", "unknown")),
            template_summary=str(narrative_section.get("template_summary", "")),
            attack_type=str(attack_section.get("likely_attack_type", "unknown")),
            attack_stage=str(attack_section.get("likely_attack_stage", "unknown")),
            analyst_recommendation=str(
                narrative_section.get("analyst_recommendation", "")
            ),
            generated_description=str(
                narrative_section.get(
                    "final_narrative", "Deterministic narrative unavailable from payload."
                )
            ),
            used_fallback=True,
        )

        return output.model_dump()
