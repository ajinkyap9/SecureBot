# SecureBot Backend: Detailed Flow, Features, Implementation, and Structure

## 1. Purpose and Scope

This document explains the current backend implementation in detail:
- how an alert enters the system,
- how detection and risk are produced,
- how explanation and analyst description are generated,
- how playbooks are selected and executed,
- exact input/output contracts,
- core file structure and responsibilities.

This reflects the current code paths under backend/app.

---

## 2. Current System Boundary

Important boundary: the backend does not currently read raw log files directly.

Current expectation:
- upstream parser/collector converts each log event into JSON,
- backend receives that JSON via API as AlertInput.

So the "log processing" inside this backend starts at API ingestion of structured alert payloads.

---

## 3. Repository Structure (Backend Core)

### Entry and API Layer
- app/main.py
- app/api/alerts.py
- app/api/detection.py
- app/api/actions.py
- app/api/approvals.py
- app/api/cases.py

### Orchestration and Agents
- app/agents/orchestrator.py
- app/agents/intel_agent.py
- app/agents/hunt_agent.py
- app/agents/detection_agent.py
- app/agents/summary_agent.py

### ML and Decision Services
- app/services/detection_service.py
- app/services/risk_service.py
- app/services/explanation_service.py
- app/services/decision_engine.py
- app/services/enrichment.py
- app/services/scoring.py

### Description Layer
- app/services/description_layer/description_service.py
- app/services/description_layer/payload_adapter.py
- app/services/description_layer/graph_builder.py
- app/services/description_layer/prompts.py
- app/services/description_layer/schemas.py

### Playbook Layer
- app/services/playbook_mapper.py
- app/services/playbook_executor.py

### Persistence and Contracts
- app/db/session.py
- app/models/alert.py
- app/models/case.py
- app/models/action.py
- app/models/approval.py
- app/schemas/alert_schema.py
- app/schemas/risk_schema.py
- app/schemas/case_schema.py
- app/schemas/approval_schema.py
- app/store/memory_store.py

### Runtime Config and Logging
- app/core/settings.py
- app/services/pipeline_logger.py

---

## 4. End-to-End Flow (From Alert JSON to Action)

## Step 0: Alert JSON arrives
Endpoint options:
- POST /alerts/ingest-detection
- POST /alerts/ingest-risk-description
- POST /alerts/ingest-full (alias)
- POST /alerts/ingest (legacy full payload route)

Primary schema: AlertInput (app/schemas/alert_schema.py)

## Step 1: Alert persistence
- Alert row is created if alert_id is not already present.
- Implemented in _persist_alert_if_missing in app/api/alerts.py.

## Step 2: Detection pipeline starts
- run_detection_pipeline(alert) in app/agents/orchestrator.py performs:
  - intel stage,
  - hunt stage,
  - detection stage,
  - detection score derivation,
  - gate decision for risk escalation.

## Step 3: Detection output derivation strategy
Order in _derive_detection_output(alert):
1. use alert.detection_output if provided,
2. else use alert.data if provided and run ML detection,
3. else derive a deterministic 33-feature vector from alert fields and run ML detection,
4. if ML inference fails, use heuristic fallback detection,
5. if derivation fails unexpectedly, return zeroed unknown detection output.

## Step 4: Risk routing gate
- should_route_to_risk(...) assigns routing points based on detection score/label, intel score/level, severity, command patterns, privilege/sensitive flags, etc.
- Gate passes when points >= 2.

## Step 5A: If gate fails (detection-only mode)
Response from /alerts/ingest-risk-description:
- mode = detection_only
- includes detection_section
- risk_section = null
- description_section = null

## Step 5B: If gate passes (risk + description mode)
- run_pipeline(...) called with defer_playbook_execution=True.
- Pipeline computes risk, explanation, enrichment, decision context.
- description payload built from pipeline result.
- description service enriches narrative (LLM if available, fallback if not).
- model2_context is assembled for playbook planning.
- playbooks selected.
- case created when required.
- playbooks executed (approval pending or simulated execution).
- final compact response returned.

## Step 6: Pipeline event logging
- Every ingest endpoint writes a pipeline event using write_pipeline_event(...).
- Event is persisted to local JSONL and may optionally be forwarded to remote API.

---

## 5. Detailed Input Contracts

## 5.1 Alert ingestion input (AlertInput)
Fields:
- required: alert_id, source, timestamp
- optional context: ip, process, command
- optional detection inputs:
  - data: list[float]
  - detection_output: { ae_score, if_score, combined_detection_score, detection_label }
- optional risk context features:
  - rule_hit_count
  - max_rule_severity
  - asset_criticality
  - public_facing_flag
  - privileged_account_flag
  - sensitive_data_flag
  - crown_jewel_flag
  - spread_count_hosts
  - ueba_score
  - lateral_movement_flag
  - persistence_flag
  - max_cvss_score
  - user_risk_score

## 5.2 Detection + risk API input (RiskAssessmentRequest)
For POST /detect/predict-with-risk:
- requires either data OR detection_output
- includes same risk feature fields as above
- validated by model_validator in risk_schema.py

---

## 6. Detailed Output Contracts

## 6.1 Detection section output
Produced by _build_detection_section in app/api/alerts.py:
- detection_output:
  - ae_score
  - if_score
  - combined_detection_score
  - detection_label
- detection_source
- intel_summary:
  - risk_score
  - risk_label
  - threat_level
  - confidence
  - attack_type
- sigma_summary:
  - title
  - level
  - approval_required
- should_run_risk
- potential_reasons

## 6.2 Risk section output
Produced in run_pipeline by risk_service + explanation_service:
- risk_score
- risk_label
- top_risk_factors
- description
- detection_source
- confidence_score
- action
- risk_model_version (xgb_v1 or heuristic_fallback)
- explanation_method (shap_tree or rules)

## 6.3 Description section output
Produced by description_layer service:
- incident_id
- alert_id
- risk_score
- risk_label
- template_summary
- attack_type
- attack_stage
- analyst_recommendation
- generated_description
- used_fallback

## 6.4 Decision section output
Returned in risk_and_description mode:
- severity
- action_mode
- selected_playbooks
- playbook_results

Each playbook result includes:
- action_id
- playbook
- status
- alert_id
- case_id
- risk_score
- attack_type

## 6.5 Legacy full pipeline output (/alerts/ingest)
Returns:
- status
- pipeline_result with keys:
  - alert
  - intel
  - hunt
  - detection
  - detection_output
  - routing
  - risk
  - enrichment
  - decision
  - summary

---

## 7. Stage-by-Stage Implementation Details

## 7.1 Intel stage
File: app/agents/intel_agent.py
- Deterministic intel heuristics over process/command.
- Calls calculate_risk_score(process, command).
- Adds ATT&CK mapping clues and reasons.
- Normalizes risk to percent and maps to threat label.

## 7.2 Hunt stage
File: app/agents/hunt_agent.py
- Builds hypotheses and query candidates from alert+intel confidence.
- Returns hunt priority and analyst note.

## 7.3 Detection stage
File: app/agents/detection_agent.py
- Produces sigma_rule candidate for suspicious powershell encoded behavior.
- Adds deployment_recommendation, false_positive_risk, approval_required.

## 7.4 Detection scoring service
File: app/services/detection_service.py
- Lazy-loads AE model, IF model, scaler, and thresholds.
- Validates feature count against trained scaler.
- Computes AE reconstruction error and IF score.
- Performs min-max normalization using saved training mins/maxes.
- Applies fusion weights and thresholds to produce detection label.

Model artifacts:
- app/ml_models/hdfs_ae_model.pt
- app/ml_models/hdfs_if_model.pkl
- app/ml_models/hdfs_scaler.pkl
- app/ml_models/hdfs_thresholds.json

## 7.5 Risk feature builder and scoring
Files:
- app/agents/orchestrator.py (_build_risk_features)
- app/services/risk_service.py

Behavior:
- Constructs risk features from detection + alert context + intel/hunt cues.
- Loads XGBoost model and ordered feature list.
- Predicts probability or raw score and normalizes to 0..100.
- Maps score to low/medium/high/critical.

## 7.6 Explanation
File: app/services/explanation_service.py
- Initializes SHAP TreeExplainer on risk model.
- Computes SHAP values.
- Picks top 5 factors by absolute contribution.
- Generates deterministic explanation text with recommendation by risk label.

## 7.7 Enrichment
File: app/services/enrichment.py
- Builds normalized context package:
  - asset_context
  - threat_context
  - detection_context
  - hunt_context
  - description text

## 7.8 Decisioning
File: app/services/decision_engine.py
- decide_severity maps normalized risk_label to severity.
- decide_action_mode uses confidence thresholds and recommended action.

Threshold constants in app/utils/constants.py:
- risk label thresholds
- decision confidence thresholds

## 7.9 Description layer
Files:
- app/services/description_layer/payload_adapter.py
- app/services/description_layer/description_service.py
- app/services/description_layer/graph_builder.py
- app/services/description_layer/prompts.py
- app/services/description_layer/schemas.py

Flow:
1. build_incident_payload_from_pipeline creates deterministic IncidentPayload.
2. AnalystDescriptionService invokes LangGraph workflow.
3. Graph validates payload, builds prompt context, calls LLM (if available), validates generated description, falls back if needed, formats final output.
4. Prompt enforces SOC tone and anti-hallucination constraints.

Fallback behavior:
- If LLM unavailable or validation fails, deterministic narrative is returned with used_fallback=True.

---

## 8. Playbook Planning and Execution

## 8.1 Playbook planning
File: app/services/playbook_mapper.py

- select_playbooks(severity, attack_type, context) is planner entry.
- Planner supports two modes:
  - LLM planning (optional)
  - deterministic dynamic fallback

LLM enablement:
- PLAYBOOK_AGENT_ENABLE_LLM=1
- optional provider/model envs for planner:
  - PLAYBOOK_LLM_PROVIDER
  - PLAYBOOK_LLM_MODEL

If LLM fails or disabled:
- _dynamic_fallback_selection(context) ranks playbooks using risk label/score, detection signals, lateral movement, privileged context, sensitive assets, etc.

## 8.2 Playbook execution
File: app/services/playbook_executor.py

Behavior:
- execute_playbooks(...) creates action records.
- High-impact playbooks -> status pending_approval.
- Other playbooks -> status simulated_execution.
- action_store in memory is updated.
- action rows are persisted in DB.

After approval:
- execute_approved_action(action_id) moves approved_for_execution to executed.

Important note:
- execution is deterministic workflow state transition; it is not direct LLM-driven external SOAR command execution.

---

## 9. Persistence Model

DB entities:
- Alert (alerts)
- Case (cases)
- Action (actions)
- Approval (approvals)

Additional in-memory runtime stores:
- approval_store
- action_store

This dual state means API behavior relies on both DB and process memory for approval/action workflow state.

---

## 10. API Reference Summary

## 10.1 Alerts API
- POST /alerts/ingest
  - legacy full payload response
- POST /alerts/ingest-detection
  - detection-only compact response
- POST /alerts/ingest-risk-description
  - gated risk + description response
- POST /alerts/ingest-full
  - alias of ingest-risk-description

## 10.2 Detection API
- POST /detect/predict
  - detection only
- POST /detect/predict-with-risk
  - detection + risk + explanation

## 10.3 Case, Approval, Action APIs
- GET /cases/
- GET /cases/{case_id}
- PATCH /cases/{case_id}
- POST /approvals/review
- GET /approvals/
- POST /actions/execute/{action_id}
- GET /actions/

---

## 11. Runtime Configuration Highlights

From app/core/settings.py:
- DATABASE_URL
- FRONTEND_CORS_ORIGINS
- APP_LOG_LEVEL
- APP_LOG_FILE_PATH
- PIPELINE_LOG_STORAGE_PATH
- PIPELINE_LOG_DB_API_URL
- PIPELINE_LOG_DB_API_PATH
- PIPELINE_LOG_FORWARD_ENABLED

Description layer model config:
- OPENAI_API_KEY
- OPENAI_MODEL
- OLLAMA_MODEL
- OLLAMA_BASE_URL

Playbook planner LLM config:
- PLAYBOOK_AGENT_ENABLE_LLM
- PLAYBOOK_LLM_PROVIDER
- PLAYBOOK_LLM_MODEL

---

## 12. Typical Processing Sequence for One Parsed Log Event

1. Upstream parser converts one log record -> AlertInput JSON.
2. Send POST /alerts/ingest-detection for first-pass triage.
3. If should_run_risk=true, send POST /alerts/ingest-risk-description.
4. Review response:
   - risk_section
   - description_section
   - decision_section
5. If playbook result is pending_approval, submit POST /approvals/review.
6. Execute approved action via POST /actions/execute/{action_id}.
7. Track case/action state via GET /cases/, GET /actions/, GET /approvals/.

---

## 13. Current Feature Matrix

Implemented:
- Structured alert ingestion APIs
- Multi-stage detection pipeline with fallback logic
- Risk model scoring and SHAP explanation
- Analyst description enrichment with LLM + fallback
- Dynamic playbook planning (LLM optional)
- Approval-gated execution flow
- Case/action/approval persistence
- Pipeline event logging to JSONL + optional forwarding

Not implemented in current backend boundary:
- Direct tail/read/parse of raw log files in backend service
- Full external SOAR action execution adapters (current execution is workflow-state based)

---

## 14. Notes for Documentation Consumers

- Use /alerts/ingest-detection + /alerts/ingest-risk-description as the recommended modern flow.
- Keep /alerts/ingest only for compatibility or deep pipeline debug payloads.
- If LLM services are unavailable, description and playbook planning still operate via deterministic fallbacks.
- For production hardening, design persistent state for approval/action stores and add API authn/authz.
