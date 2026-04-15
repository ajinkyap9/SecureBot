from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from app.services.description_layer.description_service import LLMConfig, create_chat_model

logger = logging.getLogger(__name__)


PLAYBOOK_CATALOG: dict[str, dict[str, Any]] = {
    "suspicious_login_account_compromise": {
        "title": "Suspicious Login / Account Compromise",
        "description": "Force password reset, invalidate sessions, enforce MFA, notify user and SOC.",
    },
    "malware_endpoint_infection": {
        "title": "Malware / Endpoint Infection",
        "description": "Isolate endpoint, kill malicious process, collect forensic evidence, run scan.",
    },
    "suspicious_ip_threat_intel_match": {
        "title": "Suspicious IP / Threat Intel Match",
        "description": "Block IP, enrich reputation, check historical logs, increase severity.",
    },
    "lateral_movement_containment": {
        "title": "Lateral Movement Detection",
        "description": "Contain east-west traffic, monitor impacted hosts, escalate and launch hunts.",
    },
    "privilege_escalation_containment": {
        "title": "Privilege Escalation",
        "description": "Revoke privilege, audit activity, temporarily lock affected account.",
    },
    "data_exfiltration_containment": {
        "title": "Data Exfiltration",
        "description": "Block outbound path, log transfer details, notify compliance/SOC lead.",
    },
    "critical_risk_response": {
        "title": "High Risk Alert Response",
        "description": "Immediate escalation, case creation, multi-action response, SOC lead notification.",
    },
    "alert_triage_automation": {
        "title": "Alert Triage Automation",
        "description": "Auto-enrich and assign medium-risk alerts to reduce manual toil.",
    },
    "false_positive_feedback_loop": {
        "title": "False Positive Handling",
        "description": "Capture analyst feedback, suppress repeats, and tune thresholds.",
    },
    "threat_hunting_expansion": {
        "title": "Threat Hunting",
        "description": "Generate hunt queries and correlate historical events across telemetry.",
    },
}


class PlaybookPlanOutput(BaseModel):
    selected_playbooks: list[str] = Field(default_factory=list)
    reasoning: str = ""


class PlaybookPlannerState(TypedDict, total=False):
    context: dict[str, Any]
    candidate_playbooks: list[dict[str, str]]
    llm_plan: PlaybookPlanOutput
    final_plan: PlaybookPlanOutput
    errors: list[str]


PLAYBOOK_SYSTEM_PROMPT = """You are a SOC playbook planner.
Select the most relevant playbooks dynamically based on incident context.
Do not invent playbook IDs. Choose only from provided candidate_playbooks.
Select 1 to 5 playbooks.
Prioritize containment and escalation for critical/high risk scenarios.
When present, prioritize model2_output fields: risk_score, template, and description.
"""

PLAYBOOK_USER_PROMPT = """Incident context JSON:
{incident_context_json}

Candidate playbooks JSON:
{candidate_playbooks_json}

If model2_output exists in incident context, use it as primary decision input.
Return selected_playbooks and concise reasoning.
"""


@dataclass
class DynamicPlaybookPlanner:
    llm: Any | None

    def __post_init__(self) -> None:
        self._structured_chain = None
        if self.llm is not None:
            try:
                prompt = ChatPromptTemplate.from_messages(
                    [
                        ("system", PLAYBOOK_SYSTEM_PROMPT),
                        ("human", PLAYBOOK_USER_PROMPT),
                    ]
                )
                self._structured_chain = (
                    prompt | self.llm.with_structured_output(PlaybookPlanOutput)
                )
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "Playbook planner LLM chain init failed. Falling back to deterministic mode: %s",
                    str(exc),
                )
                self._structured_chain = None

        self._graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(PlaybookPlannerState)
        graph.add_node("ingest_context", self._ingest_context)
        graph.add_node("llm_plan", self._llm_plan)
        graph.add_node("fallback_plan", self._fallback_plan)
        graph.add_node("finalize_plan", self._finalize_plan)

        graph.set_entry_point("ingest_context")
        graph.add_edge("ingest_context", "llm_plan")
        graph.add_edge("llm_plan", "fallback_plan")
        graph.add_edge("fallback_plan", "finalize_plan")
        graph.add_edge("finalize_plan", END)

        return graph.compile()

    def _ingest_context(self, state: PlaybookPlannerState) -> PlaybookPlannerState:
        context = state.get("context") or {}
        return {
            "context": context,
            "candidate_playbooks": [
                {"id": key, "title": value["title"]}
                for key, value in PLAYBOOK_CATALOG.items()
            ],
            "errors": list(state.get("errors", [])),
        }

    def _llm_plan(self, state: PlaybookPlannerState) -> PlaybookPlannerState:
        if self._structured_chain is None:
            errors = list(state.get("errors", []))
            errors.append("LLM planner unavailable")
            return {"errors": errors}

        context = state.get("context", {})
        candidates = state.get("candidate_playbooks", [])

        try:
            result = self._structured_chain.invoke(
                {
                    "incident_context_json": json.dumps(context, ensure_ascii=True, indent=2),
                    "candidate_playbooks_json": json.dumps(candidates, ensure_ascii=True, indent=2),
                }
            )
            if isinstance(result, PlaybookPlanOutput):
                return {"llm_plan": result}
            return {"llm_plan": PlaybookPlanOutput.model_validate(result)}
        except Exception as exc:
            errors = list(state.get("errors", []))
            errors.append(f"LLM planning failed: {exc}")
            return {"errors": errors}

    def _fallback_plan(self, state: PlaybookPlannerState) -> PlaybookPlannerState:
        llm_plan = state.get("llm_plan")
        if llm_plan and llm_plan.selected_playbooks:
            return {}

        context = state.get("context", {})
        selected = _dynamic_fallback_selection(context)
        return {
            "final_plan": PlaybookPlanOutput(
                selected_playbooks=selected,
                reasoning="Deterministic dynamic fallback plan generated from incident context.",
            )
        }

    def _finalize_plan(self, state: PlaybookPlannerState) -> PlaybookPlannerState:
        llm_plan = state.get("llm_plan")
        final_plan = state.get("final_plan")

        plan = llm_plan or final_plan or PlaybookPlanOutput(
            selected_playbooks=["alert_triage_automation"],
            reasoning="Default triage playbook applied.",
        )

        valid = []
        seen = set()
        for item in plan.selected_playbooks:
            if item in PLAYBOOK_CATALOG and item not in seen:
                valid.append(item)
                seen.add(item)

        if not valid:
            valid = ["alert_triage_automation"]

        return {
            "final_plan": PlaybookPlanOutput(
                selected_playbooks=valid[:5],
                reasoning=plan.reasoning,
            )
        }

    def plan(self, context: dict[str, Any]) -> PlaybookPlanOutput:
        state = self._graph.invoke({"context": context})
        output = state.get("final_plan")
        if isinstance(output, PlaybookPlanOutput):
            return output
        if isinstance(output, dict):
            return PlaybookPlanOutput.model_validate(output)
        return PlaybookPlanOutput(
            selected_playbooks=["alert_triage_automation"],
            reasoning="Planner fallback output applied.",
        )


_planner_instance: DynamicPlaybookPlanner | None = None


def _get_planner() -> DynamicPlaybookPlanner:
    global _planner_instance
    if _planner_instance is not None:
        return _planner_instance

    llm = None
    if os.getenv("PLAYBOOK_AGENT_ENABLE_LLM", "0") == "1":
        try:
            llm = create_chat_model(
                LLMConfig(
                    provider=os.getenv("PLAYBOOK_LLM_PROVIDER", "ollama"),
                    model_name=os.getenv("PLAYBOOK_LLM_MODEL"),
                    temperature=0.0,
                    timeout_seconds=20,
                )
            )
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "Playbook planner LLM unavailable, deterministic mode will be used: %s",
                str(exc),
            )
            llm = None

    _planner_instance = DynamicPlaybookPlanner(llm=llm)
    return _planner_instance


def select_playbooks(
    severity: str,
    attack_type: str,
    context: dict[str, Any] | None = None,
) -> list[str]:
    planner = _get_planner()
    merged_context = {
        "severity": severity,
        "attack_type": attack_type,
        **(context or {}),
    }
    plan = planner.plan(merged_context)
    return plan.selected_playbooks


def _dynamic_fallback_selection(context: dict[str, Any]) -> list[str]:
    risk_label = str(context.get("risk_label", context.get("severity", "low"))).lower()
    risk_score = _to_float(context.get("risk_score", 0.0))
    detection_label = str(context.get("detection_label", "unknown")).lower()
    detection_score = _to_float(context.get("combined_detection_score", 0.0))
    attack_type = str(context.get("attack_type", "unknown")).lower()
    ueba_score = _to_float(context.get("ueba_score", 0.0))
    privileged = _to_float(context.get("privileged_account_flag", 0)) > 0
    lateral = _to_float(context.get("lateral_movement_flag", 0)) > 0
    spread_hosts = _to_float(context.get("spread_count_hosts", 0))
    sensitive = _to_float(context.get("sensitive_data_flag", 0)) > 0
    intel_threat = str(context.get("threat_level", "")).lower()
    has_ip = bool(str(context.get("ip", "")).strip())

    scores: dict[str, float] = {key: 0.0 for key in PLAYBOOK_CATALOG}

    # Global severity weighting.
    if risk_label == "critical" or risk_score >= 80:
        scores["critical_risk_response"] += 4.0
        scores["threat_hunting_expansion"] += 1.0
    elif risk_label == "high" or risk_score >= 60:
        scores["threat_hunting_expansion"] += 1.0
        scores["alert_triage_automation"] += 1.0
    elif risk_label == "medium" or risk_score >= 35:
        scores["alert_triage_automation"] += 2.0
    else:
        scores["false_positive_feedback_loop"] += 1.0

    if detection_score >= 0.55 or detection_label in {"anomalous", "high_anomaly"}:
        scores["malware_endpoint_infection"] += 2.0
        scores["threat_hunting_expansion"] += 1.0

    if privileged and (ueba_score >= 0.65 or "login" in attack_type or "credential" in attack_type):
        scores["suspicious_login_account_compromise"] += 3.0
        scores["privilege_escalation_containment"] += 2.0

    if lateral or spread_hosts >= 2:
        scores["lateral_movement_containment"] += 3.0
        scores["threat_hunting_expansion"] += 1.0

    if sensitive and (risk_label in {"high", "critical"} or risk_score >= 60):
        scores["data_exfiltration_containment"] += 3.0

    if has_ip and intel_threat in {"high", "critical"}:
        scores["suspicious_ip_threat_intel_match"] += 2.5

    if "command_execution" in attack_type or "powershell" in str(context.get("process", "")).lower():
        scores["malware_endpoint_infection"] += 1.5

    if risk_label == "low" and detection_score < 0.35:
        scores["false_positive_feedback_loop"] += 2.0

    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    selected = [name for name, score in ordered if score >= 1.5][:5]

    if not selected:
        selected = ["alert_triage_automation"]

    # Always keep triage for medium/high non-critical alerts if room is available.
    if (
        risk_label in {"medium", "high"}
        and "alert_triage_automation" not in selected
        and len(selected) < 5
    ):
        selected.append("alert_triage_automation")

    return selected


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0