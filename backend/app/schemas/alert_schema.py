from typing import Optional

from pydantic import BaseModel


class AlertInput(BaseModel):
    alert_id: str
    source: str
    ip: Optional[str] = None
    process: Optional[str] = None
    command: Optional[str] = None
    timestamp: str