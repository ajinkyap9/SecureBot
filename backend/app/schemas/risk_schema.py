from typing import Optional, Union

from pydantic import BaseModel, model_validator


class DetectionOutputInput(BaseModel):
    ae_score: float
    if_score: float
    combined_detection_score: float
    detection_label: str = "unknown"


class RiskAssessmentRequest(BaseModel):
    data: Optional[list[float]] = None
    detection_output: Optional[DetectionOutputInput] = None

    rule_hit_count: Optional[Union[int, float]] = 0
    max_rule_severity: Optional[Union[int, float]] = 0
    asset_criticality: Optional[Union[int, float, str]] = 0
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

    @model_validator(mode="after")
    def validate_detection_inputs(self):
        if self.data is None and self.detection_output is None:
            raise ValueError(
                "Provide either 'data' for detection inference or 'detection_output'."
            )
        return self


class RiskAssessmentResponse(BaseModel):
    ae_score: float
    if_score: float
    combined_detection_score: float
    detection_label: str
    risk_score: float
    risk_label: str
    top_risk_factors: list[str]
    description: str
