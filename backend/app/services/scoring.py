def calculate_risk_score(process_name: str, command: str) -> float:
    """Deterministic intel risk heuristic normalized to [0, 1]."""

    process = str(process_name or "").lower()
    cmd = str(command or "").lower()

    score = 0.08

    if "powershell" in process:
        score += 0.24
    if "-enc" in cmd or "encodedcommand" in cmd:
        score += 0.24
    if "wmic" in cmd or "psexec" in cmd:
        score += 0.12
    if "schtasks" in cmd or "reg add" in cmd:
        score += 0.10
    if "mimikatz" in cmd or "lsass" in cmd:
        score += 0.20
    if "administrator" in cmd or "domain admin" in cmd or "sudo" in cmd:
        score += 0.08

    return max(0.0, min(score, 1.0))
