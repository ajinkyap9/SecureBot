from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.action import Action
from app.services.playbook_executor import execute_approved_action

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/execute/{action_id}")
def execute_action(action_id: str, db: Session = Depends(get_db)):
    result = execute_approved_action(action_id, db)

    if not result:
        raise HTTPException(status_code=404, detail="Action not found")

    return result


@router.get("/")
def list_actions(db: Session = Depends(get_db)):
    actions = db.query(Action).order_by(Action.id.desc()).all()

    return {
        "total_actions": len(actions),
        "actions": [
            {
                "action_id": action.action_id,
                "playbook": action.playbook,
                "status": action.status,
                "alert_id": action.alert_id,
                "case_id": action.case_id,
                "risk_score": action.risk_score,
                "attack_type": action.attack_type,
            }
            for action in actions
        ],
    }