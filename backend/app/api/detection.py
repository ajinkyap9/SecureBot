import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas.risk_schema import RiskAssessmentRequest, RiskAssessmentResponse
from app.services.explanation_service import ExplanationService
from app.services.detection_service import predict
from app.services.risk_service import RiskScoringService

router = APIRouter()
logger = logging.getLogger(__name__)

risk_scoring_service = RiskScoringService()
explanation_service = ExplanationService()


class DetectionRequest(BaseModel):
    data: list[float]


def initialize_risk_services() -> None:
    try:
        model = risk_scoring_service.get_model()
        explanation_service.initialize(model)
    except RuntimeError as exc:
        logger.warning("Risk services initialization skipped: %s", str(exc))

@router.post("/predict")
def detect(payload: DetectionRequest):
    try:
        return predict(payload.data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/predict-with-risk", response_model=RiskAssessmentResponse)
def detect_with_risk(payload: RiskAssessmentRequest):
    try:
        initialize_risk_services()

        if payload.data is not None:
            detection_output = predict(payload.data)
        elif payload.detection_output is not None:
            detection_output = payload.detection_output.model_dump()
        else:
            raise ValueError(
                "Either 'data' or 'detection_output' must be provided in request body."
            )

        risk_features = {
            "ae_score": detection_output.get("ae_score", 0),
            "if_score": detection_output.get("if_score", 0),
            "combined_detection_score": detection_output.get(
                "combined_detection_score", 0
            ),
            "rule_hit_count": payload.rule_hit_count,
            "max_rule_severity": payload.max_rule_severity,
            "asset_criticality": payload.asset_criticality,
            "public_facing_flag": payload.public_facing_flag,
            "privileged_account_flag": payload.privileged_account_flag,
            "sensitive_data_flag": payload.sensitive_data_flag,
            "crown_jewel_flag": payload.crown_jewel_flag,
            "spread_count_hosts": payload.spread_count_hosts,
            "ueba_score": payload.ueba_score,
            "lateral_movement_flag": payload.lateral_movement_flag,
            "persistence_flag": payload.persistence_flag,
            "max_cvss_score": payload.max_cvss_score,
            "user_risk_score": payload.user_risk_score,
        }

        risk_prediction = risk_scoring_service.predict_risk(risk_features)
        model_input_df = risk_scoring_service.build_model_input(risk_features)
        explanation = explanation_service.explain(
            model_input_df, risk_prediction["risk_label"]
        )

        detection_label = detection_output.get("detection_label", "unknown")

        return {
            "ae_score": float(detection_output.get("ae_score", 0.0)),
            "if_score": float(detection_output.get("if_score", 0.0)),
            "combined_detection_score": float(
                detection_output.get("combined_detection_score", 0.0)
            ),
            "detection_label": str(detection_label),
            "risk_score": risk_prediction["risk_score"],
            "risk_label": risk_prediction["risk_label"],
            "top_risk_factors": explanation["top_risk_factors"],
            "description": explanation["description"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc