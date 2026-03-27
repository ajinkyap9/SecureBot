import uuid

from app.models.action import Action
from app.store.memory_store import action_store


HIGH_IMPACT_PLAYBOOKS = {"block_ip_candidate", "isolate_host_candidate"}


def execute_playbooks(
    playbooks: list[str],
    alert: dict,
    intel_result: dict,
    case_id: str,
    db,
) -> list[dict]:
    results = []

    for playbook in playbooks:
        action_id = str(uuid.uuid4())

        if playbook in HIGH_IMPACT_PLAYBOOKS:
            status = "pending_approval"
        else:
            status = "simulated_execution"

        action_record = {
            "action_id": action_id,
            "playbook": playbook,
            "status": status,
            "alert_id": alert.get("alert_id"),
            "case_id": case_id,
            "risk_score": intel_result.get("risk_score"),
            "attack_type": intel_result.get("attack_type"),
        }

        action_store[action_id] = action_record

        db_action = Action(
            action_id=action_id,
            playbook=playbook,
            status=status,
            alert_id=alert.get("alert_id"),
            case_id=case_id,
            risk_score=str(intel_result.get("risk_score")),
            attack_type=intel_result.get("attack_type"),
        )
        db.add(db_action)
        db.commit()

        results.append(action_record)

    return results


def execute_approved_action(action_id: str, db=None):
    action = action_store.get(action_id)

    if not action:
        return None

    if action.get("status") != "approved_for_execution":
        return action

    action["status"] = "executed"

    if db is not None:
        db_action = db.query(Action).filter(Action.action_id == action_id).first()
        if db_action:
            db_action.status = "executed"
            db.commit()

    return action