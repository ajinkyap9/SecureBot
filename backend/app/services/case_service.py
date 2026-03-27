import uuid

from sqlalchemy.orm import Session

from app.models.case import Case


def create_case_record(
    db: Session,
    alert_id: str,
    severity: str,
    attack_type: str,
    risk_score: float,
):
    case_id = str(uuid.uuid4())
    title = f"Incident case for alert {alert_id}"

    new_case = Case(
        case_id=case_id,
        title=title,
        status="open",
        severity=severity,
        alert_id=alert_id,
        attack_type=attack_type,
        risk_score=str(risk_score),
    )

    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    return new_case