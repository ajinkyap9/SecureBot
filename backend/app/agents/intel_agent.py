from app.services.scoring import calculate_risk_score


def run_intel(alert: dict) -> dict:
    ip_address = alert.get("ip", "unknown")
    process_name = str(alert.get("process", "")).lower()
    command = str(alert.get("command", "")).lower()

    risk_score = calculate_risk_score(process_name, command)

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
        risk_score = min(risk_score + 0.10, 1.0)

    if risk_score >= 0.8:
        threat_level = "high"
    elif risk_score >= 0.5:
        threat_level = "medium"

    return {
        "ioc": {
            "ip": ip_address,
            "process": process_name
        },
        "risk_score": round(risk_score, 2),
        "confidence": round(risk_score, 2),
        "attack_type": attack_type,
        "threat_level": threat_level,
        "attack_mapping": attack_mapping,
        "reasons": reasons,
        "sources_used": ["mock_intel_logic"]
    }