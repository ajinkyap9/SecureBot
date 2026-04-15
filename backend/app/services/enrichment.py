from app.utils.constants import normalize_risk_score_percent, risk_score_to_label


def build_context_enrichment(
	alert: dict,
	intel_result: dict,
	hunt_result: dict,
	detection_result: dict,
) -> dict:
	"""Build a normalized enrichment payload for downstream decision and response."""
	risk_score = normalize_risk_score_percent(intel_result.get("risk_score", 0.0))
	risk_label = risk_score_to_label(risk_score)

	sigma_rule = detection_result.get("sigma_rule") or {}
	sigma_description = sigma_rule.get("description")
	hunt_queries = hunt_result.get("queries") or []

	description_parts = []
	if sigma_description:
		description_parts.append(sigma_description)
	description_parts.append(
		f"Incident risk is {risk_label} (score={round(risk_score, 2)})."
	)
	if hunt_queries:
		description_parts.append(
			f"{len(hunt_queries)} hunt query candidates were generated for analyst validation."
		)
	enrichment_description = " ".join(description_parts)

	return {
		"description": enrichment_description,
		"asset_context": {
			"source": alert.get("source"),
			"ip": alert.get("ip"),
			"process": alert.get("process"),
			"timestamp": alert.get("timestamp"),
		},
		"threat_context": {
			"attack_type": intel_result.get("attack_type", "unknown"),
			"threat_level": intel_result.get("threat_level", "low"),
			"risk_score": round(risk_score, 2),
			"risk_label": risk_label,
			"confidence": float(intel_result.get("confidence", 0.0) or 0.0),
		},
		"detection_context": {
			"false_positive_risk": detection_result.get(
				"false_positive_risk", "unknown"
			),
			"deployment_recommendation": detection_result.get(
				"deployment_recommendation", "manual_review_required"
			),
			"sigma_rule_title": sigma_rule.get("title"),
			"sigma_rule_level": sigma_rule.get("level"),
		},
		"hunt_context": {
			"priority": hunt_result.get("priority", "low"),
			"query_count": len(hunt_queries),
		},
	}
