import logging
import ipaddress
import math

from app.agents.intel_agent import run_intel
from app.agents.hunt_agent import run_hunt
from app.agents.detection_agent import run_detection
from app.agents.summary_agent import run_summary
from app.services.case_service import create_case_record
from app.services.detection_service import predict as detect_predict
from app.services.decision_engine import decide_severity, decide_action_mode
from app.services.enrichment import build_context_enrichment
from app.services.explanation_service import ExplanationService
from app.services.playbook_mapper import select_playbooks
from app.services.playbook_executor import execute_playbooks
from app.services.risk_service import RiskScoringService
from app.utils.constants import normalize_risk_score_percent, risk_score_to_label

logger = logging.getLogger(__name__)

risk_scoring_service = RiskScoringService()
explanation_service = ExplanationService()
_risk_runtime_ready = False


def _initialize_risk_runtime() -> None:
    global _risk_runtime_ready

    if _risk_runtime_ready:
        return

    model = risk_scoring_service.get_model()
    explanation_service.initialize(model)
    _risk_runtime_ready = True


def _action_from_label(risk_label: str) -> str:
    mapping = {
        "low": "monitor",
        "medium": "triage",
        "high": "urgent_review",
        "critical": "immediate_response",
    }
    return mapping.get(risk_label, "triage")


def _confidence_from_score(risk_score: float) -> float:
    # A bounded confidence heuristic based on distance from neutral zone.
    if risk_score >= 80:
        return 0.92
    if risk_score >= 60:
        return 0.84
    if risk_score >= 30:
        return 0.76
    return 0.68


def _severity_to_numeric(level: str | None) -> float:
    mapping = {
        "critical": 10.0,
        "high": 8.0,
        "medium": 5.0,
        "low": 2.0,
    }
    return mapping.get(str(level or "").lower(), 0.0)


def _derive_detection_output(alert: dict) -> tuple[dict, str]:
    provided_detection = alert.get("detection_output")
    if isinstance(provided_detection, dict):
        return (
            {
                "ae_score": float(provided_detection.get("ae_score", 0.0) or 0.0),
                "if_score": float(provided_detection.get("if_score", 0.0) or 0.0),
                "combined_detection_score": float(
                    provided_detection.get("combined_detection_score", 0.0) or 0.0
                ),
                "detection_label": str(
                    provided_detection.get("detection_label", "unknown")
                ),
            },
            "provided",
        )

    raw_features = alert.get("data")
    if isinstance(raw_features, list) and raw_features:
        try:
            return detect_predict(raw_features), "computed"
        except Exception as exc:
            logger.warning(
                "Detection inference failed for provided raw feature vector. "
                "Using heuristic detection fallback: %s",
                str(exc),
            )
            return _heuristic_detection_output(alert), "heuristic_from_raw_features"

    # If only raw alert fields are present, derive a deterministic 33-feature
    # vector so AE/IF scoring still runs end-to-end.
    try:
        derived_features = _build_detection_feature_vector(alert)
        try:
            return detect_predict(derived_features), "computed_from_derived_features"
        except Exception as exc:
            logger.warning(
                "Detection inference failed for derived feature vector. "
                "Using heuristic detection fallback: %s",
                str(exc),
            )
            return _heuristic_detection_output(alert), "heuristic_from_derived_features"
    except Exception as exc:
        logger.warning(
            "Detection feature derivation failed. Falling back to zeroed detection scores: %s",
            str(exc),
        )

    return {
        "ae_score": 0.0,
        "if_score": 0.0,
        "combined_detection_score": 0.0,
        "detection_label": "unknown",
    }, "derived"


def _heuristic_detection_output(alert: dict) -> dict:
    """Deterministic fallback detection when AE/IF runtime is unavailable."""

    process = str(alert.get("process", "") or "").lower()
    command = str(alert.get("command", "") or "").lower()
    source = str(alert.get("source", "") or "").lower()

    ae_score = 0.0
    if_score = 0.0

    if "powershell" in process:
        ae_score += 0.20
        if_score += 0.24
    if "-enc" in command or "encodedcommand" in command:
        ae_score += 0.20
        if_score += 0.24
    if "invoke-expression" in command or " iex" in command or "iex " in command:
        ae_score += 0.18
        if_score += 0.20
    if "wmic" in command or "psexec" in command:
        ae_score += 0.16
        if_score += 0.16
    if _safe_float(alert.get("privileged_account_flag", 0)) > 0:
        ae_score += 0.12
        if_score += 0.12
    if _safe_float(alert.get("lateral_movement_flag", 0)) > 0:
        ae_score += 0.10
        if_score += 0.10
    if _safe_float(alert.get("persistence_flag", 0)) > 0:
        ae_score += 0.08
        if_score += 0.10
    if source in {"wazuh", "zeek"}:
        ae_score += 0.04
        if_score += 0.04

    ae_score = max(0.0, min(ae_score, 1.0))
    if_score = max(0.0, min(if_score, 1.0))
    combined_score = 0.6 * ae_score + 0.4 * if_score

    if combined_score >= 0.75:
        label = "high_anomaly"
    elif combined_score >= 0.55:
        label = "anomalous"
    elif combined_score >= 0.35:
        label = "suspicious"
    else:
        label = "normal"

    return {
        "ae_score": round(ae_score, 4),
        "if_score": round(if_score, 4),
        "combined_detection_score": round(combined_score, 4),
        "detection_label": label,
    }


def _build_risk_features(
    alert: dict,
    intel_result: dict,
    hunt_result: dict,
    detection_result: dict,
    detection_output: dict,
) -> dict:
    sigma_level = (detection_result.get("sigma_rule") or {}).get("level")
    hunt_queries = hunt_result.get("queries") or []
    command = str(alert.get("command", "")).lower()

    ueba_from_alert = _safe_float(alert.get("ueba_score", 0))
    if ueba_from_alert <= 0:
        ueba_from_alert = _safe_float(intel_result.get("confidence", 0.0))

    return {
        "ae_score": detection_output.get("ae_score", 0.0),
        "if_score": detection_output.get("if_score", 0.0),
        "combined_detection_score": detection_output.get("combined_detection_score", 0.0),
        "rule_hit_count": alert.get("rule_hit_count", len(hunt_queries)),
        "max_rule_severity": alert.get(
            "max_rule_severity", _severity_to_numeric(sigma_level)
        ),
        "asset_criticality": alert.get("asset_criticality", "medium"),
        "public_facing_flag": alert.get("public_facing_flag", 0),
        "privileged_account_flag": alert.get(
            "privileged_account_flag",
            1 if ("admin" in command or "root" in command) else 0,
        ),
        "sensitive_data_flag": alert.get("sensitive_data_flag", 0),
        "crown_jewel_flag": alert.get("crown_jewel_flag", 0),
        "spread_count_hosts": alert.get("spread_count_hosts", 0),
        "ueba_score": ueba_from_alert,
        "lateral_movement_flag": alert.get(
            "lateral_movement_flag", 1 if "wmic" in command else 0
        ),
        "persistence_flag": alert.get(
            "persistence_flag", 1 if ("schtasks" in command or "reg add" in command) else 0
        ),
        "max_cvss_score": alert.get("max_cvss_score", 0),
        "user_risk_score": alert.get(
            "user_risk_score", intel_result.get("risk_score", 0.0)
        ),
    }


def _build_detection_feature_vector(alert: dict) -> list[float]:
    command = str(alert.get("command", "") or "")
    lowered_command = command.lower()
    process = str(alert.get("process", "") or "")
    lowered_process = process.lower()
    source = str(alert.get("source", "") or "").lower()
    timestamp = str(alert.get("timestamp", "") or "")

    hour, weekday = _extract_time_parts(timestamp)
    ip_value = str(alert.get("ip", "") or "")

    has_ip = 1.0 if ip_value else 0.0
    is_private_ip = 1.0 if _is_private_ip(ip_value) else 0.0

    command_tokens = [token for token in lowered_command.split() if token]

    raw_user_risk = _safe_float(alert.get("user_risk_score", 0.0))
    user_risk_norm = raw_user_risk / 100.0 if raw_user_risk > 1 else raw_user_risk

    raw_ueba = _safe_float(alert.get("ueba_score", 0.0))
    ueba_norm = raw_ueba / 100.0 if raw_ueba > 1 else raw_ueba

    feature_vector = [
        min(len(command) / 200.0, 1.0),  # 1 command length
        min(len(process) / 40.0, 1.0),  # 2 process name length
        _contains_any(lowered_process, ["powershell"]),  # 3
        _contains_any(lowered_command, ["-enc", "encodedcommand"]),  # 4
        _contains_any(lowered_command, ["invoke-expression", " iex", "iex "]),  # 5
        _contains_any(lowered_command, ["wmic", "psexec"]),  # 6
        _contains_any(lowered_command, ["schtasks", "task scheduler"]),  # 7
        _contains_any(lowered_command, ["reg add", "runonce", "startup"]),  # 8
        _contains_any(lowered_command, ["administrator", "domain admin", "sudo"]),  # 9
        _contains_any(lowered_command, ["root ", " su "]),  # 10
        has_ip,  # 11
        is_private_ip,  # 12
        1.0 if source == "wazuh" else 0.0,  # 13
        1.0 if source in {"auth", "auth_logs", "auth logs"} else 0.0,  # 14
        1.0 if source in {"endpoint", "endpoint_logs", "endpoint logs"} else 0.0,  # 15
        1.0 if source == "zeek" else 0.0,  # 16
        (math.sin((2 * math.pi * hour) / 24.0) + 1.0) / 2.0,  # 17
        (math.cos((2 * math.pi * hour) / 24.0) + 1.0) / 2.0,  # 18
        weekday / 6.0,  # 19
        min(_safe_float(alert.get("rule_hit_count", 0.0)) / 20.0, 1.0),  # 20
        min(_safe_float(alert.get("max_rule_severity", 0.0)) / 10.0, 1.0),  # 21
        min(_asset_criticality_to_num(alert.get("asset_criticality", "medium")) / 4.0, 1.0),  # 22
        _to_flag(alert.get("public_facing_flag", 0.0)),  # 23
        _to_flag(alert.get("privileged_account_flag", 0.0)),  # 24
        _to_flag(alert.get("sensitive_data_flag", 0.0)),  # 25
        _to_flag(alert.get("crown_jewel_flag", 0.0)),  # 26
        min(_safe_float(alert.get("spread_count_hosts", 0.0)) / 10.0, 1.0),  # 27
        max(0.0, min(ueba_norm, 1.0)),  # 28
        _to_flag(alert.get("lateral_movement_flag", 0.0)),  # 29
        _to_flag(alert.get("persistence_flag", 0.0)),  # 30
        min(_safe_float(alert.get("max_cvss_score", 0.0)) / 10.0, 1.0),  # 31
        max(0.0, min(user_risk_norm, 1.0)),  # 32
        min(len(command_tokens) / 40.0, 1.0),  # 33 token count
    ]

    return feature_vector


def _safe_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _contains_any(text: str, tokens: list[str]) -> float:
    return 1.0 if any(token in text for token in tokens) else 0.0


def _to_flag(value) -> float:
    return 1.0 if _safe_float(value) > 0 else 0.0


def _asset_criticality_to_num(value) -> float:
    if isinstance(value, str):
        mapping = {
            "low": 1.0,
            "medium": 2.0,
            "high": 3.0,
            "critical": 4.0,
        }
        mapped = mapping.get(value.strip().lower())
        if mapped is not None:
            return mapped
    return _safe_float(value)


def _is_private_ip(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).is_private
    except ValueError:
        return False


def _extract_time_parts(timestamp: str) -> tuple[int, int]:
    # Supports ISO timestamps (e.g. 2026-04-05T12:05:00Z). Falls back safely.
    try:
        from datetime import datetime

        cleaned = timestamp.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        return dt.hour, dt.weekday()
    except Exception:
        return 12, 0


def _is_escalation_detection_label(label: str) -> bool:
    return label in {"suspicious", "anomalous", "high_anomaly", "malicious"}


def should_route_to_risk(
    alert: dict,
    intel_result: dict,
    detection_result: dict,
    detection_output: dict,
) -> tuple[bool, list[str]]:
    """Gate to decide whether risk scoring + description should run."""

    reasons: list[str] = []
    routing_points = 0

    def _append_reason(text: str) -> None:
        if text not in reasons:
            reasons.append(text)

    combined = _safe_float(detection_output.get("combined_detection_score", 0.0))
    detection_label = str(detection_output.get("detection_label", "unknown") or "").lower()
    intel_percent = normalize_risk_score_percent(intel_result.get("risk_score", 0.0))
    threat_level = str(
        intel_result.get("threat_level", intel_result.get("risk_label", ""))
    ).lower()

    severity_raw = alert.get("max_rule_severity", 0)
    if isinstance(severity_raw, str):
        severity_score = _severity_to_numeric(severity_raw)
    else:
        severity_score = _safe_float(severity_raw)

    rule_hit_count = _safe_float(alert.get("rule_hit_count", 0))
    command = str(alert.get("command", "") or "").lower()
    privileged_flag = _safe_float(alert.get("privileged_account_flag", 0)) > 0
    sensitive_flag = _safe_float(alert.get("sensitive_data_flag", 0)) > 0
    crown_jewel_flag = _safe_float(alert.get("crown_jewel_flag", 0)) > 0
    encoded_command = "-enc" in command or "encodedcommand" in command

    if combined >= 0.55:
        routing_points += 2
        _append_reason(
            f"Combined detection score {combined:.2f} exceeded escalation threshold."
        )
    elif combined >= 0.40 and _is_escalation_detection_label(detection_label):
        routing_points += 1
        _append_reason(
            f"Detection score {combined:.2f} with label {detection_label} suggests suspicious behavior."
        )

    if detection_label == "high_anomaly":
        routing_points += 2
        _append_reason("Detection label is high_anomaly.")

    if threat_level in {"high", "critical"}:
        routing_points += 2
        _append_reason(f"Intel threat level is {threat_level}.")
    if intel_percent >= 65.0:
        routing_points += 2
        _append_reason(
            f"Intel risk score {intel_percent:.2f} is above escalation threshold."
        )

    if severity_score >= 8.0:
        routing_points += 2
        _append_reason(f"Rule severity {severity_score:.1f} indicates high impact.")
    elif severity_score >= 6.0:
        routing_points += 1
        _append_reason(f"Rule severity {severity_score:.1f} indicates elevated impact.")

    if rule_hit_count >= 10.0:
        routing_points += 1
        _append_reason(f"Rule hit count {rule_hit_count:.0f} indicates repeated activity.")

    if (
        detection_result.get("approval_required")
        and encoded_command
    ):
        routing_points += 2
        _append_reason("Encoded command with approval-required detection was observed.")

    if privileged_flag and ("powershell" in command or "wmic" in command):
        routing_points += 1
        _append_reason("Privileged account executed a high-risk command pattern.")

    if sensitive_flag or crown_jewel_flag:
        routing_points += 1
        _append_reason("Sensitive or crown-jewel asset context increases potential impact.")

    return routing_points >= 2, reasons[:6]


def run_detection_pipeline(alert: dict) -> dict:
    """Run only detection-related stages for high-volume ingestion."""

    intel_result = run_intel(alert)
    hunt_result = run_hunt(alert, intel_result)
    detection_result = run_detection(alert, intel_result, hunt_result)
    detection_output, detection_source = _derive_detection_output(alert)

    potential_for_risk, potential_reasons = should_route_to_risk(
        alert=alert,
        intel_result=intel_result,
        detection_result=detection_result,
        detection_output=detection_output,
    )

    return {
        "alert": alert,
        "intel": intel_result,
        "hunt": hunt_result,
        "detection": detection_result,
        "detection_output": detection_output,
        "detection_source": detection_source,
        "potential_for_risk": potential_for_risk,
        "potential_reasons": potential_reasons,
    }


def run_pipeline(
    alert: dict,
    db,
    detection_bundle: dict | None = None,
    defer_playbook_execution: bool = False,
) -> dict:
    if detection_bundle is None:
        detection_bundle = run_detection_pipeline(alert)

    intel_result = detection_bundle["intel"]
    hunt_result = detection_bundle["hunt"]
    detection_result = detection_bundle["detection"]
    detection_output = detection_bundle["detection_output"]
    detection_source = detection_bundle["detection_source"]
    should_run_risk = bool(detection_bundle.get("potential_for_risk", False))
    potential_reasons = detection_bundle.get("potential_reasons", [])

    risk_score_for_decision = normalize_risk_score_percent(
        intel_result.get("risk_score", 0.0)
    )

    try:
        _initialize_risk_runtime()
        risk_features = _build_risk_features(
            alert=alert,
            intel_result=intel_result,
            hunt_result=hunt_result,
            detection_result=detection_result,
            detection_output=detection_output,
        )

        risk_prediction = risk_scoring_service.predict_risk(risk_features)
        model_input_df = risk_scoring_service.build_model_input(risk_features)
        explanation = explanation_service.explain(
            model_input_df, risk_prediction["risk_label"]
        )

        risk_score_for_decision = normalize_risk_score_percent(
            risk_prediction.get("risk_score", 0.0)
        )
        risk_label = str(
            risk_prediction.get("risk_label")
            or risk_score_to_label(risk_score_for_decision)
        )
        risk_result = {
            "risk_score": risk_score_for_decision,
            "risk_label": risk_label,
            "top_risk_factors": explanation["top_risk_factors"],
            "description": explanation["description"],
            "detection_source": detection_source,
            "confidence_score": _confidence_from_score(risk_score_for_decision),
            "action": _action_from_label(risk_label),
            "risk_model_version": "xgb_v1",
            "explanation_method": "shap_tree",
        }
    except Exception as exc:
        logger.warning("Falling back to heuristic risk in pipeline: %s", str(exc))
        heuristic_percent = normalize_risk_score_percent(risk_score_for_decision)
        heuristic_label = RiskScoringService.score_to_label(heuristic_percent)

        risk_result = {
            "risk_score": heuristic_percent,
            "risk_label": heuristic_label,
            "top_risk_factors": [],
            "description": "Fallback heuristic risk scoring was used because model inference was unavailable.",
            "detection_source": detection_source,
            "confidence_score": _confidence_from_score(heuristic_percent),
            "action": _action_from_label(heuristic_label),
            "risk_model_version": "heuristic_fallback",
            "explanation_method": "rules",
        }

    intel_result["risk_score"] = float(risk_result.get("risk_score", 0.0) or 0.0)
    intel_result["risk_label"] = str(risk_result.get("risk_label", "low"))
    intel_result["threat_level"] = intel_result["risk_label"]
    intel_result["confidence"] = round(
        min(1.0, float(risk_result.get("confidence_score", 0.0) or 0.0)), 2
    )

    enrichment_result = build_context_enrichment(
        alert=alert,
        intel_result=intel_result,
        hunt_result=hunt_result,
        detection_result=detection_result,
    )
    threat_context = enrichment_result.setdefault("threat_context", {})
    threat_context["risk_score"] = risk_result.get("risk_score")
    threat_context["risk_label"] = risk_result.get("risk_label")
    threat_context["confidence"] = risk_result.get(
        "confidence_score", threat_context.get("confidence")
    )
    enrichment_result["description"] = risk_result.get(
        "description", enrichment_result.get("description", "")
    )

    attack_type = intel_result.get("attack_type", "unknown")

    severity = decide_severity(risk_result.get("risk_label", "low"))
    action_mode = decide_action_mode(
        risk_label=risk_result.get("risk_label", "low"),
        confidence_score=float(risk_result.get("confidence_score", 0.0) or 0.0),
        action=risk_result.get("action"),
    )
    planner_context = {
        "alert_id": alert.get("alert_id"),
        "ip": alert.get("ip"),
        "process": alert.get("process"),
        "user": alert.get("user"),
        "risk_score": float(risk_result.get("risk_score", 0.0) or 0.0),
        "risk_label": str(risk_result.get("risk_label", "low")),
        "detection_label": detection_output.get("detection_label"),
        "combined_detection_score": detection_output.get("combined_detection_score"),
        "threat_level": intel_result.get("threat_level", intel_result.get("risk_label", "")),
        "ueba_score": alert.get("ueba_score"),
        "privileged_account_flag": alert.get("privileged_account_flag"),
        "lateral_movement_flag": alert.get("lateral_movement_flag"),
        "spread_count_hosts": alert.get("spread_count_hosts"),
        "sensitive_data_flag": alert.get("sensitive_data_flag"),
    }
    selected_playbooks = (
        [] if defer_playbook_execution else select_playbooks(severity, attack_type, context=planner_context)
    )

    case_required_playbooks = {
        "critical_risk_response",
        "suspicious_login_account_compromise",
        "malware_endpoint_infection",
        "suspicious_ip_threat_intel_match",
        "lateral_movement_containment",
        "privilege_escalation_containment",
        "data_exfiltration_containment",
    }
    should_create_case = severity in {"high", "critical"} or any(
        playbook in case_required_playbooks for playbook in selected_playbooks
    )

    created_case = None
    if should_create_case:
        created_case = create_case_record(
            db=db,
            alert_id=alert.get("alert_id"),
            severity=severity,
            attack_type=attack_type,
            risk_score=float(risk_result.get("risk_score", 0.0) or 0.0),
        )

    if defer_playbook_execution:
        playbook_results = []
    else:
        playbook_results = execute_playbooks(
            selected_playbooks,
            alert,
            intel_result,
            created_case.case_id if created_case else None,
            db,
        )

    decision_result = {
        "severity": severity,
        "action_mode": action_mode,
        "selected_playbooks": selected_playbooks,
        "playbook_results": playbook_results,
        "case_id": created_case.case_id if created_case else None,
    }

    summary_result = run_summary(
        alert=alert,
        intel_result=intel_result,
        hunt_result=hunt_result,
        detection_result=detection_result,
        decision_result=decision_result
    )

    return {
        "alert": alert,
        "intel": intel_result,
        "hunt": hunt_result,
        "detection": detection_result,
        "detection_output": detection_output,
        "routing": {
            "should_run_risk": should_run_risk,
            "potential_reasons": potential_reasons,
        },
        "risk": risk_result,
        "enrichment": enrichment_result,
        "decision": decision_result,
        "summary": summary_result,
    }