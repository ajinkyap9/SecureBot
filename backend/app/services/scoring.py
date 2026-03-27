def calculate_risk_score(process: str, command: str) -> float:
    score = 0.20

    process = (process or "").lower()
    command = (command or "").lower()

    if "powershell" in process:
        score += 0.25

    if "-enc" in command or "encodedcommand" in command:
        score += 0.35

    if "invoke-expression" in command or "iex" in command:
        score += 0.20

    return min(score, 1.0)