from app.utils.constants import DECISION_CONFIDENCE_THRESHOLDS


def decide_severity(risk_label: str) -> str:
    normalized_label = str(risk_label or "").lower()
    if normalized_label in {"low", "medium", "high", "critical"}:
        return normalized_label
    return "low"


def decide_action_mode(
    risk_label: str,
    confidence_score: float,
    action: str | None = None,
) -> str:
    label = str(risk_label or "").lower()
    confidence = float(confidence_score or 0.0)
    risk_action = str(action or "").lower()

    if label == "critical":
        if (
            confidence >= DECISION_CONFIDENCE_THRESHOLDS["critical_approval_required"]
            and risk_action == "immediate_response"
        ):
            return "approval_required"
        return "analyst_review"

    if label == "high":
        if (
            confidence >= DECISION_CONFIDENCE_THRESHOLDS["high_approval_required"]
            and risk_action in {"immediate_response", "urgent_review"}
        ):
            return "approval_required"
        if confidence >= DECISION_CONFIDENCE_THRESHOLDS["high_analyst_review"]:
            return "analyst_review"
        return "log_only"

    if label == "medium":
        if confidence >= DECISION_CONFIDENCE_THRESHOLDS["medium_analyst_review"]:
            return "analyst_review"
        return "log_only"

    return "log_only"