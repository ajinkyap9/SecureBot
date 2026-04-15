"""Project-wide constants."""

# Percent-space thresholds used by model-backed risk labeling.
RISK_LABEL_THRESHOLDS_PERCENT = {
	"critical": 75.0,
	"high": 60.0,
	"medium": 30.0,
}

# Confidence thresholds used by decisioning logic.
DECISION_CONFIDENCE_THRESHOLDS = {
	"critical_approval_required": 0.90,
	"high_approval_required": 0.90,
	"high_analyst_review": 0.60,
	"medium_analyst_review": 0.80,
}


def normalize_risk_score_percent(raw_score) -> float:
	"""Normalize an arbitrary risk score to a bounded 0..100 percent scale."""
	try:
		score = float(raw_score)
	except (TypeError, ValueError):
		score = 0.0

	if score <= 1.0:
		score *= 100.0

	score = max(0.0, min(100.0, score))
	return round(score, 2)


def risk_score_to_label(risk_score: float) -> str:
	"""Map a percent-scale score to a unified risk label."""
	if risk_score >= RISK_LABEL_THRESHOLDS_PERCENT["critical"]:
		return "critical"
	if risk_score >= RISK_LABEL_THRESHOLDS_PERCENT["high"]:
		return "high"
	if risk_score >= RISK_LABEL_THRESHOLDS_PERCENT["medium"]:
		return "medium"
	return "low"
