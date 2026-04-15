from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.orchestrator import run_detection_pipeline, run_pipeline
from app.db.session import SessionLocal
from app.models.alert import Alert
from app.schemas.alert_schema import AlertInput
from app.services.case_service import create_case_record
from app.services.description_layer.description_service import AnalystDescriptionService
from app.services.description_layer.payload_adapter import (
    build_incident_payload_from_pipeline,
)
from app.services.pipeline_logger import write_pipeline_event
from app.services.playbook_executor import HIGH_IMPACT_PLAYBOOKS, execute_playbooks
from app.services.playbook_mapper import select_playbooks

router = APIRouter()
description_service = AnalystDescriptionService()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/ingest")
def ingest_alert(alert: AlertInput, db: Session = Depends(get_db)):
    try:
        result = _persist_and_run_pipeline(alert, db)
        response_payload = {
            "status": "success",
            "pipeline_result": result,
        }
        _log_pipeline_event(
            endpoint="/alerts/ingest",
            mode="full",
            alert_payload=alert.model_dump(),
            response_payload=response_payload,
        )

        return response_payload
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/ingest-detection")
def ingest_alert_detection(alert: AlertInput, db: Session = Depends(get_db)):
    """Run detection stages for every log and return compact routing decision."""

    try:
        _persist_alert_if_missing(alert, db)

        detection_bundle = run_detection_pipeline(alert.model_dump())
        detection_section = _build_detection_section(detection_bundle)

        response_payload = {
            "status": "success",
            "mode": "detection_only",
            "alert_id": alert.alert_id,
            "detection_section": detection_section,
        }
        _log_pipeline_event(
            endpoint="/alerts/ingest-detection",
            mode="detection_only",
            alert_payload=alert.model_dump(),
            response_payload=response_payload,
        )

        return response_payload
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/ingest-risk-description")
def ingest_alert_risk_description(alert: AlertInput, db: Session = Depends(get_db)):
    """Run risk scoring + description only when alert passes potential gate."""

    try:
        return _run_gated_risk_description_flow(alert, db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/ingest-full")
def ingest_alert_full(alert: AlertInput, db: Session = Depends(get_db)):
    """Backward-compatible alias for gated risk+description flow."""

    try:
        return _run_gated_risk_description_flow(alert, db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def _run_gated_risk_description_flow(alert: AlertInput, db: Session) -> dict:
    _persist_alert_if_missing(alert, db)
    alert_payload = alert.model_dump()

    detection_bundle = run_detection_pipeline(alert_payload)
    detection_section = _build_detection_section(detection_bundle)

    if not detection_section["should_run_risk"]:
        response_payload = {
            "status": "success",
            "mode": "detection_only",
            "alert_id": alert.alert_id,
            "detection_section": detection_section,
            "risk_section": None,
            "description_section": None,
            "message": (
                "Alert did not meet potential-threat gate. "
                "Risk scoring and description were skipped."
            ),
        }
        _log_pipeline_event(
            endpoint="/alerts/ingest-risk-description",
            mode="detection_only",
            alert_payload=alert_payload,
            response_payload=response_payload,
        )
        return response_payload

    pipeline_result = run_pipeline(
        alert_payload,
        db,
        detection_bundle=detection_bundle,
        defer_playbook_execution=True,
    )
    incident_payload = build_incident_payload_from_pipeline(
        alert_payload=alert_payload,
        pipeline_result=pipeline_result,
    )
    description_result = description_service.enrich_description(incident_payload)

    decision = dict(pipeline_result.get("decision") or {})
    intel_section = pipeline_result.get("intel") or {}
    risk_section = pipeline_result.get("risk") or {}
    severity = str(decision.get("severity", "low"))
    attack_type = str(intel_section.get("attack_type", "unknown"))

    model2_context = _build_model2_playbook_context(
        alert_payload=alert_payload,
        risk_section=risk_section,
        description_section=description_result,
        detection_section=detection_section,
        intel_section=intel_section,
    )
    selected_playbooks = select_playbooks(
        severity=severity,
        attack_type=attack_type,
        context=model2_context,
    )

    case_id = decision.get("case_id")
    if not case_id and any(pb in HIGH_IMPACT_PLAYBOOKS for pb in selected_playbooks):
        created_case = create_case_record(
            db=db,
            alert_id=str(alert_payload.get("alert_id", "unknown")),
            severity=severity,
            attack_type=attack_type,
            risk_score=float(risk_section.get("risk_score", 0.0) or 0.0),
        )
        case_id = created_case.case_id

    playbook_results = execute_playbooks(
        selected_playbooks,
        alert_payload,
        intel_section,
        case_id,
        db,
    )

    decision["selected_playbooks"] = selected_playbooks
    decision["playbook_results"] = playbook_results
    decision["case_id"] = case_id
    pipeline_result["decision"] = decision

    response_payload = {
        "status": "success",
        "mode": "risk_and_description",
        "alert_id": alert.alert_id,
        "detection_section": detection_section,
        "risk_section": risk_section,
        "description_section": description_result,
        "decision_section": {
            "severity": decision.get("severity"),
            "action_mode": decision.get("action_mode"),
            "selected_playbooks": selected_playbooks,
            "playbook_results": playbook_results,
        },
        "case_id": case_id,
    }
    _log_pipeline_event(
        endpoint="/alerts/ingest-risk-description",
        mode="risk_and_description",
        alert_payload=alert_payload,
        response_payload=response_payload,
    )
    return response_payload


def _build_detection_section(detection_bundle: dict) -> dict:
    intel = detection_bundle.get("intel") or {}
    detection = detection_bundle.get("detection") or {}
    sigma_rule = detection.get("sigma_rule") or {}

    return {
        "detection_output": detection_bundle.get("detection_output", {}),
        "detection_source": detection_bundle.get("detection_source", "unknown"),
        "intel_summary": {
            "risk_score": float(intel.get("risk_score", 0.0) or 0.0),
            "risk_label": str(intel.get("risk_label", intel.get("threat_level", "low"))),
            "threat_level": str(intel.get("threat_level", "low")),
            "confidence": float(intel.get("confidence", 0.0) or 0.0),
            "attack_type": str(intel.get("attack_type", "unknown")),
        },
        "sigma_summary": {
            "title": sigma_rule.get("title"),
            "level": sigma_rule.get("level"),
            "approval_required": bool(detection.get("approval_required", False)),
        },
        "should_run_risk": bool(detection_bundle.get("potential_for_risk", False)),
        "potential_reasons": detection_bundle.get("potential_reasons", []),
    }


def _persist_and_run_pipeline(alert: AlertInput, db: Session) -> dict:
    _persist_alert_if_missing(alert, db)
    return run_pipeline(alert.model_dump(), db)


def _build_model2_playbook_context(
    alert_payload: dict,
    risk_section: dict,
    description_section: dict,
    detection_section: dict,
    intel_section: dict,
) -> dict:
    return {
        "alert_id": alert_payload.get("alert_id"),
        "ip": alert_payload.get("ip"),
        "process": alert_payload.get("process"),
        "user": alert_payload.get("user"),
        "risk_score": float(risk_section.get("risk_score", 0.0) or 0.0),
        "risk_label": str(risk_section.get("risk_label", "low")),
        "threat_level": str(
            intel_section.get("threat_level", intel_section.get("risk_label", "low"))
        ),
        "detection_label": str(
            (detection_section.get("detection_output") or {}).get(
                "detection_label", "unknown"
            )
        ),
        "combined_detection_score": float(
            (detection_section.get("detection_output") or {}).get(
                "combined_detection_score", 0.0
            )
            or 0.0
        ),
        "template_summary": str(description_section.get("template_summary", "")),
        "generated_description": str(
            description_section.get("generated_description", "")
        ),
        "model2_output": {
            "risk_score": float(risk_section.get("risk_score", 0.0) or 0.0),
            "template": str(description_section.get("template_summary", "")),
            "description": str(description_section.get("generated_description", "")),
        },
        "ueba_score": float(alert_payload.get("ueba_score", 0.0) or 0.0),
        "privileged_account_flag": float(
            alert_payload.get("privileged_account_flag", 0.0) or 0.0
        ),
        "lateral_movement_flag": float(
            alert_payload.get("lateral_movement_flag", 0.0) or 0.0
        ),
        "spread_count_hosts": float(alert_payload.get("spread_count_hosts", 0.0) or 0.0),
        "sensitive_data_flag": float(alert_payload.get("sensitive_data_flag", 0.0) or 0.0),
    }


def _log_pipeline_event(
    endpoint: str,
    mode: str,
    alert_payload: dict,
    response_payload: dict,
) -> None:
    try:
        write_pipeline_event(
            endpoint=endpoint,
            mode=mode,
            alert_id=str(alert_payload.get("alert_id", "")),
            request_payload=alert_payload,
            response_payload=response_payload,
        )
    except Exception:
        # Logging must never fail the API response path.
        return


def _persist_alert_if_missing(alert: AlertInput, db: Session) -> None:
    existing_alert = db.query(Alert).filter(Alert.alert_id == alert.alert_id).first()

    if not existing_alert:
        db_alert = Alert(
            alert_id=alert.alert_id,
            source=alert.source,
            ip=alert.ip,
            process=alert.process,
            command=alert.command,
            timestamp=alert.timestamp,
        )
        db.add(db_alert)
        db.commit()