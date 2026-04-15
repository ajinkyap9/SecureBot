# SecureBot Backend Pipeline and API Guide

## 1) Scope
This document describes the implemented backend pipeline only:
- Detection for every ingested alert
- Gated risk scoring and description generation for potential alerts only
- Case, approval, and action execution endpoints

No frontend or dashboard content is included.

---

## 2) What Is Implemented

## 2.1 Core pipeline behavior
The backend now supports a 2-stage security workflow:
1. Stage A: Detection stage runs for every alert.
2. Stage B: Risk scoring + analyst description runs only when the routing gate marks the alert as potential.

## 2.2 Key pipeline functions
- Detection stage function: `run_detection_pipeline(...)`
- Full deterministic pipeline function: `run_pipeline(...)`
- Risk routing gate function: `should_route_to_risk(...)`

## 2.3 Detection score sourcing order
Detection output is derived in this order:
1. Use `detection_output` from request if provided.
2. Else use `data` vector if provided.
3. Else derive 33-feature vector from raw alert fields and run detection.
4. If ML inference is unavailable, apply deterministic heuristic fallback detection.

---

## 3) End-to-End Processing Flow

1. Alert received via `/alerts/*` endpoint.
2. Alert is persisted if not already present.
3. Detection stage runs:
   - Intel analysis
   - Hunt hypothesis/query generation
   - Detection rule generation
   - AE/IF/combined detection output
4. Routing gate evaluates escalation conditions.
5. If gate is false:
   - Return detection result only.
6. If gate is true:
   - Build risk features
   - Run risk model + explanation
   - Build enrichment and decision
   - Execute selected playbooks and create/update case as needed
   - Build description-layer payload
   - Generate analyst description (LLM if available, deterministic fallback otherwise)

---

## 4) Input Contract

Primary alert input model used by `/alerts/*` endpoints:

```json
{
  "alert_id": "string (required)",
  "source": "string (required)",
  "timestamp": "ISO string (required)",
  "ip": "string (optional)",
  "process": "string (optional)",
  "command": "string (optional)",

  "data": [0.1, 0.2, "..."],
  "detection_output": {
    "ae_score": 0.0,
    "if_score": 0.0,
    "combined_detection_score": 0.0,
    "detection_label": "unknown"
  },

  "rule_hit_count": 0,
  "max_rule_severity": 0,
  "asset_criticality": "medium",
  "public_facing_flag": 0,
  "privileged_account_flag": 0,
  "sensitive_data_flag": 0,
  "crown_jewel_flag": 0,
  "spread_count_hosts": 0,
  "ueba_score": 0,
  "lateral_movement_flag": 0,
  "persistence_flag": 0,
  "max_cvss_score": 0,
  "user_risk_score": 0
}
```

Notes:
- You do not need to send `data` for normal ingestion.
- You do not need to send `detection_output` unless you want to override upstream detection.

---

## 5) API Catalog and Usage

Base URL example:
- `http://127.0.0.1:8001`

## 5.1 Alerts APIs

### A) Detection for every alert
- Method: `POST`
- Path: `/alerts/ingest-detection`
- Purpose: Run detection stage and return routing decision only.

Response shape:
```json
{
  "status": "success",
  "mode": "detection_only",
  "alert_id": "...",
  "detection_section": {
    "detection_output": {
      "ae_score": 0.0,
      "if_score": 0.0,
      "combined_detection_score": 0.0,
      "detection_label": "normal|suspicious|anomalous|high_anomaly|unknown"
    },
    "detection_source": "provided|computed|computed_from_derived_features|heuristic_*|derived",
    "intel_summary": {
      "risk_score": 0.0,
      "risk_label": "low|medium|high|critical",
      "threat_level": "low|medium|high|critical",
      "confidence": 0.0,
      "attack_type": "..."
    },
    "sigma_summary": {
      "title": "...",
      "level": "...",
      "approval_required": true
    },
    "should_run_risk": false,
    "potential_reasons": ["..."]
  }
}
```

### B) Gated risk + description
- Method: `POST`
- Path: `/alerts/ingest-risk-description`
- Purpose: Run risk and description only if routing gate passes.

If not escalated:
```json
{
  "status": "success",
  "mode": "detection_only",
  "alert_id": "...",
  "detection_section": {"...": "..."},
  "risk_section": null,
  "description_section": null,
  "message": "Alert did not meet potential-threat gate. Risk scoring and description were skipped."
}
```

If escalated:
```json
{
  "status": "success",
  "mode": "risk_and_description",
  "alert_id": "...",
  "detection_section": {"...": "..."},
  "risk_section": {
    "risk_score": 0.0,
    "risk_label": "...",
    "top_risk_factors": ["..."],
    "description": "...",
    "detection_source": "...",
    "confidence_score": 0.0,
    "action": "monitor|triage|urgent_review|immediate_response",
    "risk_model_version": "xgb_v1|heuristic_fallback",
    "explanation_method": "shap_tree|rules"
  },
  "description_section": {
    "incident_id": "...",
    "alert_id": "...",
    "risk_score": 0.0,
    "risk_label": "...",
    "template_summary": "...",
    "attack_type": "...",
    "attack_stage": "...",
    "analyst_recommendation": "...",
    "generated_description": "...",
    "used_fallback": true
  },
  "decision_section": {
    "severity": "high|critical|medium|low",
    "action_mode": "approval_required|analyst_review|log_only",
    "selected_playbooks": ["..."],
    "playbook_results": [
      {
        "action_id": "...",
        "playbook": "...",
        "status": "pending_approval|simulated_execution",
        "alert_id": "...",
        "case_id": "..."
      }
    ]
  },
  "case_id": "..."
}
```

Notes:
- `decision_section.selected_playbooks` is planned using the LLM playbook agent when enabled.
- The planner receives model-2 fields from risk/description output (`risk_score`, `template_summary`, `generated_description`) as primary context.

### C) Backward-compatible alias
- Method: `POST`
- Path: `/alerts/ingest-full`
- Purpose: Alias of `/alerts/ingest-risk-description`.

### D) Legacy full deterministic response
- Method: `POST`
- Path: `/alerts/ingest`
- Purpose: Return full pipeline payload (`pipeline_result`) regardless of compact gating response format.

---

## 5.2 Detection APIs (`/detect`)

### A) Detection only from feature vector
- Method: `POST`
- Path: `/detect/predict`
- Body:
```json
{
  "data": [0.0, 0.1, "... exactly model feature count ..."]
}
```

### B) Detection + risk in one request
- Method: `POST`
- Path: `/detect/predict-with-risk`
- Body options:
  - Provide `data`, or
  - Provide `detection_output`
  - Plus risk context features

Returns:
- detection scores + label
- risk score + label
- top risk factors
- risk description

---

## 5.3 Case, Approval, and Action APIs

### A) Review action approval
- Method: `POST`
- Path: `/approvals/review`
- Purpose: Approve/reject pending action.

### B) Execute approved action
- Method: `POST`
- Path: `/actions/execute/{action_id}`
- Purpose: Execute action by action id.

### C) List actions
- Method: `GET`
- Path: `/actions/`
- Purpose: Fetch latest playbook execution/action state.

### C) Cases
- `GET /cases/` : list cases
- `GET /cases/{case_id}` : case detail
- `PATCH /cases/{case_id}` : update case status

### D) List approvals
- Method: `GET`
- Path: `/approvals/`
- Purpose: Fetch approval history for actions.

---

## 6) Recommended Operational API Sequence

Use this sequence in production-style testing:

1. Send every incoming alert to `POST /alerts/ingest-detection`.
2. Check `detection_section.should_run_risk`.
3. If false: stop there (detection-only handling).
4. If true: call `POST /alerts/ingest-risk-description`.
5. Use `case_id` and playbook outputs to drive approvals/execution:
   - `POST /approvals/review`
   - `POST /actions/execute/{action_id}`
   - `GET/PATCH /cases/*`

---

## 7) Postman Request Syntax (Quick)

Headers for all JSON requests:
- `Content-Type: application/json`

Example environment variable:
- `base_url = http://127.0.0.1:8001`

Then call:
- `POST {{base_url}}/alerts/ingest-detection`
- `POST {{base_url}}/alerts/ingest-risk-description`

---

## 8) Error Handling

Common status behavior:
- `200`: success response
- `400`: invalid input format or missing required detection inputs
- `404`: missing resource (case/action)
- `500`: internal processing error
- `503`: ML dependency/model unavailable for specific predict endpoints

---

## 9) LLM Description Fallback Behavior

`description_section.used_fallback` indicates narrative source:
- `false`: LLM-generated structured output succeeded.
- `true`: deterministic fallback narrative was used (for example provider not configured/unreachable).

This does not invalidate deterministic detection/risk outputs.

---

## 10) Environment Variables

Use `backend/.env.example` as the template.

Important runtime keys:
- `DATABASE_URL`: SQLAlchemy database connection string.
- `PIPELINE_LOG_STORAGE_PATH`: local folder path for jsonl pipeline event logs.
- `PIPELINE_LOG_DB_API_URL`: base URL for optional external database API sink.
- `PIPELINE_LOG_DB_API_PATH`: path appended to base URL for pipeline event writes.
- `PIPELINE_LOG_FORWARD_ENABLED`: toggle remote forwarding on/off.
- `PLAYBOOK_AGENT_ENABLE_LLM`, `PLAYBOOK_LLM_PROVIDER`, `PLAYBOOK_LLM_MODEL`: playbook planner LLM controls.
