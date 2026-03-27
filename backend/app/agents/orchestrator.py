from app.agents.intel_agent import run_intel
from app.agents.hunt_agent import run_hunt
from app.agents.detection_agent import run_detection
from app.agents.summary_agent import run_summary
from app.services.case_service import create_case_record
from app.services.decision_engine import decide_severity, decide_action_mode
from app.services.playbook_mapper import select_playbooks
from app.services.playbook_executor import execute_playbooks


def run_pipeline(alert: dict, db) -> dict:
    intel_result = run_intel(alert)
    hunt_result = run_hunt(alert, intel_result)
    detection_result = run_detection(alert, intel_result, hunt_result)

    risk_score = intel_result.get("risk_score", 0.0)
    attack_type = intel_result.get("attack_type", "unknown")

    severity = decide_severity(risk_score)
    action_mode = decide_action_mode(risk_score)
    selected_playbooks = select_playbooks(severity, attack_type)

    created_case = None
    if "create_case" in selected_playbooks:
        created_case = create_case_record(
            db=db,
            alert_id=alert.get("alert_id"),
            severity=severity,
            attack_type=attack_type,
            risk_score=risk_score,
        )

    playbook_results = execute_playbooks(
        selected_playbooks,
        alert,
        intel_result,
        created_case.case_id if created_case else None,
        db,
    )

    decision_result = {
        "severity": severity,
        "action_mode": action_mode,
        "selected_playbooks": selected_playbooks,
        "playbook_results": playbook_results,
        "case_id": created_case.case_id if created_case else None,
    }

    summary_result = run_summary(
        alert=alert,
        intel_result=intel_result,
        hunt_result=hunt_result,
        detection_result=detection_result,
        decision_result=decision_result
    )

    return {
        "alert": alert,
        "intel": intel_result,
        "hunt": hunt_result,
        "detection": detection_result,
        "decision": decision_result,
        "summary": summary_result,
    }