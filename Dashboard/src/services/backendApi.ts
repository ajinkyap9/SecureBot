export interface AlertInputPayload {
  alert_id: string
  source: string
  ip: string
  process: string
  command?: string | null
  timestamp: string
  host?: string | null
  user?: string | null
  severity?: string | null
  detection_score?: number | null
  event_count?: number | null
}

export interface DetectionOnlyResponse {
  status: string
  mode: 'detection_only' | 'risk_and_description'
  alert_id: string
  detection_section: {
    detection_output: Record<string, unknown>
    detection_source: string
    intel_summary: {
      risk_score: number
      risk_label: string
      threat_level: string
      confidence: number
      attack_type: string
    }
    sigma_summary: {
      title?: string
      level?: string
      approval_required: boolean
    }
    should_run_risk: boolean
    potential_reasons: string[]
  }
  risk_section?: Record<string, unknown> | null
  description_section?: Record<string, unknown> | null
  decision_section?: {
    severity?: string
    action_mode?: string
    selected_playbooks?: string[]
    playbook_results?: Array<{
      action_id: string
      playbook: string
      status: string
      alert_id: string
      case_id?: string | null
      risk_score?: number
      attack_type?: string
    }>
  }
  message?: string
  case_id?: string | null
}

export interface CaseListResponse {
  total_cases: number
  cases: Array<{
    case_id: string
    title: string
    status: string
    severity: string
    alert_id: string
    attack_type: string
    risk_score: string
  }>
}

export interface ActionListResponse {
  total_actions: number
  actions: Array<{
    action_id: string
    playbook: string
    status: string
    alert_id: string
    case_id?: string | null
    risk_score?: string | null
    attack_type?: string | null
  }>
}

export interface ApprovalListResponse {
  total_approvals: number
  approvals: Array<{
    action_id: string
    approved: boolean
    analyst: string
    comment?: string | null
  }>
}

const backendBaseUrl = import.meta.env.VITE_BACKEND_URL ?? 'http://127.0.0.1:8001'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${backendBaseUrl}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || `Request failed with status ${response.status}`)
  }

  return response.json() as Promise<T>
}

export async function runDetectionOnly(payload: AlertInputPayload): Promise<DetectionOnlyResponse> {
  return request<DetectionOnlyResponse>('/alerts/ingest-detection', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function runRiskAndDescription(
  payload: AlertInputPayload,
): Promise<DetectionOnlyResponse> {
  return request<DetectionOnlyResponse>('/alerts/ingest-risk-description', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function fetchCases(): Promise<CaseListResponse> {
  return request<CaseListResponse>('/cases/')
}

export async function fetchActions(): Promise<ActionListResponse> {
  return request<ActionListResponse>('/actions/')
}

export async function fetchApprovals(): Promise<ApprovalListResponse> {
  return request<ApprovalListResponse>('/approvals/')
}
