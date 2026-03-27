from typing import Optional

from pydantic import BaseModel


class ApprovalRequest(BaseModel):
    action_id: str
    approved: bool
    analyst: str
    comment: Optional[str] = None