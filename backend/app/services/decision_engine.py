
def decide_severity(risk_score: float) -> str:
    if risk_score >= 0.8:
        return "high"
    if risk_score >= 0.5:
        return "medium"
    return "low"


def decide_action_mode(risk_score: float) -> str:
    if risk_score >= 0.8:
        return "approval_required"
    if risk_score >= 0.5:
        return "analyst_review"
    return "log_only"