def select_playbooks(severity: str, attack_type: str) -> list[str]:
    if severity == "high":
        if attack_type == "command_execution":
            return ["create_case", "notify_analyst", "block_ip_candidate"]
        return ["create_case", "notify_analyst"]

    if severity == "medium":
        if attack_type == "command_execution":
            return ["create_case", "notify_analyst"]
        return ["notify_analyst"]

    return ["log_event_only"]