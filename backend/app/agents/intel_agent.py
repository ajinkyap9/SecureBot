from app.services.scoring import calculate_risk_score
from app.utils.constants import normalize_risk_score_percent, risk_score_to_label


def run_intel(alert: dict) -> dict:
    ip_address = alert.get("ip", "unknown")
    process_name = str(alert.get("process", "")).lower()
    command = str(alert.get("command", "")).lower()

    risk_score_normalized = calculate_risk_score(process_name, command)

    attack_mapping = []
    reasons = []
    attack_type = "unknown"
    threat_level = "low"

    if "powershell" in process_name:
        attack_type = "command_execution"
        attack_mapping.append({
            "technique_id": "T1059.001",
            "technique_name": "PowerShell"
        })
        reasons.append("PowerShell process observed")

    if "-enc" in command or "encodedcommand" in command:
        attack_mapping.append({
            "technique_id": "T1027",
            "technique_name": "Obfuscated/Compressed Files and Information"
        })
        reasons.append("Encoded PowerShell command detected")

    if "invoke-expression" in command or "iex" in command:
        reasons.append("Potential suspicious execution pattern detected")
        risk_score_normalized = min(risk_score_normalized + 0.10, 1.0)

    risk_score = normalize_risk_score_percent(risk_score_normalized)
    threat_level = risk_score_to_label(risk_score)

    return {
        "ioc": {
            "ip": ip_address,
            "process": process_name
        },
        "risk_score": risk_score,
        "confidence": round(risk_score_normalized, 2),
        "attack_type": attack_type,
        "threat_level": threat_level,
        "attack_mapping": attack_mapping,
        "reasons": reasons,
        "sources_used": ["mock_intel_logic"]
    }