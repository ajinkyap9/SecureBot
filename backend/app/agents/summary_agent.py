def run_summary(
    alert: dict,
    intel_result: dict,
    hunt_result: dict,
    detection_result: dict,
    decision_result: dict
) -> dict:
    attack_mapping = intel_result.get("attack_mapping", [])
    attack_ids = [item.get("technique_id") for item in attack_mapping]

    return {
        "executive_summary": (
            "The alert was enriched, analyzed for hunting opportunities, mapped to "
            "possible ATT&CK techniques, and processed through a risk-based playbook decision flow."
        ),
        "technical_summary": {
            "alert_source": alert.get("source"),
            "process": alert.get("process"),
            "ip": alert.get("ip"),
            "risk_score": intel_result.get("risk_score"),
            "confidence": intel_result.get("confidence"),
            "threat_level": intel_result.get("threat_level"),
            "attack_type": intel_result.get("attack_type"),
            "mapped_attack_techniques": attack_ids,
            "hunt_priority": hunt_result.get("priority"),
            "selected_playbooks": decision_result.get("selected_playbooks", [])
        },
        "recommended_next_action": [
            "Validate whether the observed activity is legitimate or malicious.",
            "Review the selected playbooks and pending approvals.",
            "Approve high-impact response actions only after analyst verification."
        ],
        "detection_summary": {
            "rule_generated": detection_result.get("sigma_rule") is not None,
            "approval_required": detection_result.get("approval_required", False)
        }
    }