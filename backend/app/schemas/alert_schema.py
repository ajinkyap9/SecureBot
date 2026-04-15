from typing import Optional, Union

from pydantic import BaseModel


class DetectionOutputInput(BaseModel):
    ae_score: float
    if_score: float
    combined_detection_score: float
    detection_label: str = "unknown"


class AlertInput(BaseModel):
    alert_id: str
    source: str
    ip: Optional[str] = None
    process: Optional[str] = None
    command: Optional[str] = None
    timestamp: str

    # Optional detection payload from upstream systems.
    data: Optional[list[float]] = None
    detection_output: Optional[DetectionOutputInput] = None

    # Optional context features for model-backed risk scoring.
    rule_hit_count: Optional[Union[int, float]] = 0
    max_rule_severity: Optional[Union[int, float]] = 0
    asset_criticality: Optional[Union[int, float, str]] = "medium"
    public_facing_flag: Optional[Union[int, float]] = 0
    privileged_account_flag: Optional[Union[int, float]] = 0
    sensitive_data_flag: Optional[Union[int, float]] = 0
    crown_jewel_flag: Optional[Union[int, float]] = 0
    spread_count_hosts: Optional[Union[int, float]] = 0
    ueba_score: Optional[Union[int, float]] = 0
    lateral_movement_flag: Optional[Union[int, float]] = 0
    persistence_flag: Optional[Union[int, float]] = 0
    max_cvss_score: Optional[Union[int, float]] = 0
    user_risk_score: Optional[Union[int, float]] = 0