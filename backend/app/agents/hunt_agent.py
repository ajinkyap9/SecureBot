def run_hunt(alert: dict, intel_result: dict) -> dict:
    process_name = str(alert.get("process", "")).lower()
    command = str(alert.get("command", "")).lower()
    confidence = intel_result.get("confidence", 0.0)

    hypotheses = []
    queries = []
    priority = "low"

    if "powershell" in process_name and ("-enc" in command or "encodedcommand" in command):
        hypotheses.append("Investigate suspicious encoded PowerShell execution.")
        queries.append({
            "type": "siem_query",
            "query": "process_name='powershell.exe' AND command_line CONTAINS '-enc'"
        })
        queries.append({
            "type": "process_hunt",
            "query": "Review parent-child process chain for powershell.exe"
        })

    if confidence >= 0.8:
        priority = "high"
    elif confidence >= 0.5:
        priority = "medium"

    if not hypotheses:
        hypotheses.append("No strong hunt hypothesis generated from current alert.")
        queries.append({
            "type": "generic",
            "query": "Review surrounding process execution, user activity, and nearby alerts."
        })

    return {
        "hypotheses": hypotheses,
        "queries": queries,
        "priority": priority,
        "analyst_note": "Review hunt queries before using them in production SIEM."
    }