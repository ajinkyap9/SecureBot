from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
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