def run_detection(alert: dict, intel_result: dict, hunt_result: dict) -> dict:
    process_name = str(alert.get("process", "")).lower()
    command = str(alert.get("command", "")).lower()

    sigma_rule = None
    false_positive_risk = "medium"
    deployment_recommendation = "manual_review_required"

    if "powershell" in process_name and "-enc" in command:
        sigma_rule = {
            "title": "Suspicious Encoded PowerShell Execution",
            "id": "11111111-2222-3333-4444-555555555555",
            "status": "experimental",
            "description": "Detects PowerShell execution with encoded command arguments.",
            "logsource": {
                "product": "windows",
                "category": "process_creation"
            },
            "detection": {
                "selection": {
                    "Image|endswith": "\\powershell.exe",
                    "CommandLine|contains": "-enc"
                },
                "condition": "selection"
            },
            "level": "high"
        }
        false_positive_risk = "low"

    return {
        "sigma_rule": sigma_rule,
        "backend_query_candidates": hunt_result.get("queries", []),
        "deployment_recommendation": deployment_recommendation,
        "false_positive_risk": false_positive_risk,
        "approval_required": True
    }