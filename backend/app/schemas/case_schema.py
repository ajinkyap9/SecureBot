from typing import Optional

from pydantic import BaseModel, ConfigDict


class CaseCreateResponse(BaseModel):
    case_id: str
    title: str
    status: str
    severity: str
    alert_id: str
    attack_type: Optional[str] = None
    risk_score: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CaseUpdateRequest(BaseModel):
    status: str


class CaseResponse(BaseModel):
    case_id: str
    title: str
    status: str
    severity: str
    alert_id: str
    attack_type: Optional[str] = None
    risk_score: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)