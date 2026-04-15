from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field


class TemplateExplanationItem(BaseModel):
    """Single template explanation produced by deterministic SHAP/template layer."""

    feature: str
    template: str
    feature_value: float | int | str | None = None
    shap_value: float | int | None = None
    impact: Literal["increase", "decrease"] | str = "increase"


class DetectionSection(BaseModel):
    ae_score: float
    if_score: float
    combined_detection_score: float
    detection_label: str


class RiskSection(BaseModel):
    risk_score_raw: float | None = None
    risk_score: float
    risk_label: str
    confidence_score: float | None = None
    top_risk_factors: list[str] = Field(default_factory=list)
    risk_reducing_factors: list[str] = Field(default_factory=list)
    template_explanations_positive: list[TemplateExplanationItem] = Field(
        default_factory=list
    )
    template_explanations_negative: list[TemplateExplanationItem] = Field(
        default_factory=list
    )


class ContextSection(BaseModel):
    rule_hit_count: int | float = 0
    max_rule_severity: int | float = 0
    asset_criticality: int | float | str = 0
    public_facing_flag: int | float = 0
    privileged_account_flag: int | float = 0
    sensitive_data_flag: int | float = 0
    crown_jewel_flag: int | float = 0
    spread_count_hosts: int | float = 0
    ueba_score: int | float = 0
    lateral_movement_flag: int | float = 0
    persistence_flag: int | float = 0
    max_cvss_score: int | float = 0
    user_risk_score: int | float = 0


class AttackAssessmentSection(BaseModel):
    likely_attack_type: str = "unknown"
    likely_attack_stage: str = "unknown"
    attack_reasoning: str = ""


class NarrativeSection(BaseModel):
    template_summary: str = ""
    final_narrative: str = ""
    analyst_recommendation: str = ""


class LlmInputReadySection(BaseModel):
    risk_score: float | None = None
    risk_label: str | None = None
    detection_label: str | None = None
    positive_evidence: list[str] = Field(default_factory=list)
    negative_evidence: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    likely_attack_type: str | None = None
    likely_attack_stage: str | None = None
    template_summary: str | None = None
    final_narrative: str | None = None
    analyst_recommendation: str | None = None


class IncidentPayload(BaseModel):
    """Final deterministic payload produced by risk pipeline."""

    model_config = ConfigDict(extra="allow")

    incident_id: str
    alert_id: str
    source: str | None = None
    timestamp: str | None = None
    summary: str | None = None
    detection: DetectionSection
    risk: RiskSection
    context: ContextSection
    attack_assessment: AttackAssessmentSection
    narrative: NarrativeSection
    llm_input_ready: LlmInputReadySection = Field(default_factory=LlmInputReadySection)


class PromptContext(BaseModel):
    """Compact evidence context fed to LLM prompt."""

    incident_id: str
    alert_id: str
    source: str | None = None
    timestamp: str | None = None
    summary: str = ""
    risk_score: float
    risk_label: str
    confidence_score: float | None = None
    detection_label: str
    template_summary: str
    attack_type: str
    attack_stage: str
    attack_reasoning: str = ""
    analyst_recommendation: str
    top_risk_factors: list[str] = Field(default_factory=list)
    reducing_factors: list[str] = Field(default_factory=list)
    positive_evidence: list[str] = Field(default_factory=list)
    negative_evidence: list[str] = Field(default_factory=list)


class AnalystDescriptionDraft(BaseModel):
    """Structured LLM output for analyst narrative text only."""

    generated_description: str = Field(
        ..., description="SOC analyst-style enriched incident description in 4-6 sentences."
    )


class DescriptionPipelineOutput(BaseModel):
    """Final response contract returned by description service."""

    incident_id: str
    alert_id: str
    risk_score: float
    risk_label: str
    template_summary: str
    attack_type: str
    attack_stage: str
    analyst_recommendation: str
    generated_description: str
    used_fallback: bool


class DescriptionGraphState(TypedDict, total=False):
    """LangGraph state for deterministic + LLM description workflow."""

    input_payload: dict[str, Any]
    incident: IncidentPayload
    prompt_context: PromptContext
    llm_result: AnalystDescriptionDraft
    generated_description: str
    used_fallback: bool
    errors: list[str]
    output: DescriptionPipelineOutput
