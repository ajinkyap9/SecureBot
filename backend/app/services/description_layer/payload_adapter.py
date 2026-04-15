from __future__ import annotations

from typing import Any


CONTEXT_KEYS = [
    "rule_hit_count",
    "max_rule_severity",
    "asset_criticality",
    "public_facing_flag",
    "privileged_account_flag",
    "sensitive_data_flag",
    "crown_jewel_flag",
    "spread_count_hosts",
    "ueba_score",
    "lateral_movement_flag",
    "persistence_flag",
    "max_cvss_score",
    "user_risk_score",
]


def build_incident_payload_from_pipeline(
    alert_payload: dict[str, Any],
    pipeline_result: dict[str, Any],
) -> dict[str, Any]:
    """Build deterministic incident payload for description layer.

    This adapter does not alter any existing risk outputs. It only reshapes
    existing pipeline data into the contract consumed by description enrichment.
    """

    risk = pipeline_result.get("risk", {})
    intel = pipeline_result.get("intel", {})
    summary = pipeline_result.get("summary", {})
    detection_output = _resolve_detection_output(alert_payload, pipeline_result)

    alert_id = str(alert_payload.get("alert_id", "unknown"))
    incident_id = str(alert_payload.get("incident_id") or f"INC-{alert_id}")

    risk_score = float(risk.get("risk_score", 0.0) or 0.0)
    risk_label = str(risk.get("risk_label", "low"))
    top_risk_factors = _ensure_str_list(risk.get("top_risk_factors", []))

    attack_type = str(intel.get("attack_type", "unknown"))
    attack_stage = _infer_attack_stage(attack_type, alert_payload)

    recommended_actions = summary.get("recommended_next_action") or []
    analyst_recommendation = (
        str(recommended_actions[0])
        if isinstance(recommended_actions, list) and recommended_actions
        else "Review the incident and apply containment actions based on policy."
    )

    template_summary = (
        f"Risk is {risk_label} ({risk_score:.2f}) based on deterministic scoring. "
        f"Primary drivers: {', '.join(top_risk_factors[:3]) if top_risk_factors else 'none listed'}."
    )

    reducing_factors = _derive_reducing_factors(pipeline_result)

    positive_evidence = _build_positive_evidence(intel, risk, top_risk_factors)
    negative_evidence = reducing_factors.copy()

    deterministic_narrative = str(risk.get("description", "")).strip() or str(
        summary.get("executive_summary", "")
    )

    context = {key: alert_payload.get(key, 0) for key in CONTEXT_KEYS}

    return {
        "incident_id": incident_id,
        "alert_id": alert_id,
        "source": alert_payload.get("source", "unknown"),
        "timestamp": alert_payload.get("timestamp", ""),
        "summary": str(summary.get("executive_summary", "") or ""),
        "detection": {
            "ae_score": float(detection_output.get("ae_score", 0.0) or 0.0),
            "if_score": float(detection_output.get("if_score", 0.0) or 0.0),
            "combined_detection_score": float(
                detection_output.get("combined_detection_score", 0.0) or 0.0
            ),
            "detection_label": str(detection_output.get("detection_label", "unknown")),
        },
        "risk": {
            "risk_score_raw": round(risk_score / 100.0, 6),
            "risk_score": risk_score,
            "risk_label": risk_label,
            "confidence_score": float(risk.get("confidence_score", 0.0) or 0.0),
            "top_risk_factors": top_risk_factors,
            "risk_reducing_factors": reducing_factors,
            "template_explanations_positive": _build_template_items(
                top_risk_factors,
                impact="increase",
            ),
            "template_explanations_negative": _build_template_items(
                reducing_factors,
                impact="decrease",
            ),
        },
        "context": context,
        "attack_assessment": {
            "likely_attack_type": attack_type,
            "likely_attack_stage": attack_stage,
            "attack_reasoning": "; ".join(_ensure_str_list(intel.get("reasons", []))),
        },
        "narrative": {
            "template_summary": template_summary,
            "final_narrative": deterministic_narrative,
            "analyst_recommendation": analyst_recommendation,
        },
        "llm_input_ready": {
            "risk_score": risk_score,
            "risk_label": risk_label,
            "detection_label": str(detection_output.get("detection_label", "unknown")),
            "positive_evidence": positive_evidence,
            "negative_evidence": negative_evidence,
            "context": context,
            "likely_attack_type": attack_type,
            "likely_attack_stage": attack_stage,
            "template_summary": template_summary,
            "final_narrative": deterministic_narrative,
            "analyst_recommendation": analyst_recommendation,
        },
    }


def _resolve_detection_output(
    alert_payload: dict[str, Any], pipeline_result: dict[str, Any]
) -> dict[str, Any]:
    detection_output = pipeline_result.get("detection_output")
    if isinstance(detection_output, dict):
        return detection_output

    provided = alert_payload.get("detection_output")
    if isinstance(provided, dict):
        return provided

    return {
        "ae_score": 0.0,
        "if_score": 0.0,
        "combined_detection_score": 0.0,
        "detection_label": "unknown",
    }


def _build_positive_evidence(
    intel: dict[str, Any],
    risk: dict[str, Any],
    top_risk_factors: list[str],
) -> list[str]:
    evidence: list[str] = []

    for reason in _ensure_str_list(intel.get("reasons", [])):
        evidence.append(reason)

    for factor in top_risk_factors[:5]:
        evidence.append(f"Risk driver identified: {factor}.")

    description = str(risk.get("description", "")).strip()
    if description:
        evidence.append(description)

    # Keep evidence deterministic and compact.
    return evidence[:12]


def _derive_reducing_factors(pipeline_result: dict[str, Any]) -> list[str]:
    detection_result = pipeline_result.get("detection", {})
    false_positive_risk = str(detection_result.get("false_positive_risk", "")).lower()

    reducing: list[str] = []
    if false_positive_risk in {"medium", "high"}:
        reducing.append(
            f"Detection false-positive risk assessed as {false_positive_risk}."
        )

    return reducing


def _build_template_items(features: list[str], impact: str) -> list[dict[str, Any]]:
    template_items: list[dict[str, Any]] = []
    for feature in features[:5]:
        feature_name = str(feature)
        template_items.append(
            {
                "feature": feature_name,
                "template": f"{feature_name.replace('_', ' ')} contributes to incident risk assessment.",
                "feature_value": 0.0,
                "shap_value": 0.0,
                "impact": impact,
            }
        )
    return template_items


def _infer_attack_stage(attack_type: str, alert_payload: dict[str, Any]) -> str:
    lowered_type = (attack_type or "").strip().lower()

    if lowered_type in {"command_execution", "execution"}:
        return "execution"
    if lowered_type in {"credential abuse", "credential_access"}:
        return "credential access"

    if float(alert_payload.get("lateral_movement_flag", 0) or 0) > 0:
        return "lateral movement"
    if float(alert_payload.get("persistence_flag", 0) or 0) > 0:
        return "persistence"

    return "unknown"


def _ensure_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]
