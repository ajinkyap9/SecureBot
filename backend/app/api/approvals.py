from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.action import Action
from app.models.approval import Approval
from app.schemas.approval_schema import ApprovalRequest
from app.store.memory_store import approval_store, action_store

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/review")
def review_action(request: ApprovalRequest, db: Session = Depends(get_db)):
    if request.action_id not in action_store:
        raise HTTPException(status_code=404, detail="Action ID not found")

    approval_store[request.action_id] = {
        "approved": request.approved,
        "analyst": request.analyst,
        "comment": request.comment
    }

    current_action = action_store[request.action_id]
    current_action["approval"] = approval_store[request.action_id]

    if request.approved:
        current_action["status"] = "approved_for_execution"
    else:
        current_action["status"] = "rejected"

    db_approval = Approval(
        action_id=request.action_id,
        approved=request.approved,
        analyst=request.analyst,
        comment=request.comment,
    )
    db.add(db_approval)

    db_action = db.query(Action).filter(Action.action_id == request.action_id).first()
    if db_action:
        db_action.status = current_action["status"]

    db.commit()

    return {
        "status": "recorded",
        "action_id": request.action_id,
        "decision": approval_store[request.action_id],
        "updated_action": current_action,
    }