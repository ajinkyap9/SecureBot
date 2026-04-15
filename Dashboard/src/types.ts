export type Severity = 'Low' | 'Medium' | 'High' | 'Critical'

export type AlertStatus = 'New' | 'Under Review' | 'Escalated' | 'Resolved'

export type CaseStatus =
  | 'New'
  | 'Investigating'
  | 'Awaiting approval'
  | 'Contained'
  | 'Resolved'
  | 'Closed'

export interface TimelineEvent {
  time: string
  event: string
  source: string
  user: string
  host: string
  ip: string
  pivot: string
}

export interface FeatureContribution {
  feature: string
  impact: number
  reason: string
}

export interface RiskFactor {
  factor: string
  weight: number
  detail: string
}

export interface AlertModelScores {
  ae: number
  iforest: number
  combined: number
  xgboostRisk: number
  confidence: number
}

export interface AlertRecord {
  id: string
  timestamp: string
  host: string
  user: string
  ip: string
  process: string
  fileHash: string
  detectionLabel: string
  alertType: string
  anomalyScore: number
  riskScore: number
  severity: Severity
  mitreTechnique: string
  mitreTactic: string
  status: AlertStatus
  source: string
  privileged: boolean
  crownJewel: boolean
  summary: string
  rawEvent: string
  parsedFeatures: Array<{ key: string; value: string | number }>
  modelScores: AlertModelScores
  explainability: FeatureContribution[]
  riskFactors: RiskFactor[]
  humanReasons: string[]
  relatedEvents: TimelineEvent[]
  recommendedNextStep: string
}

export interface OverviewMetrics {
  totalEventsIngested: number
  totalAlertsGenerated: number
  openIncidents: number
  highCriticalAlerts: number
  meanTimeToDetectMinutes: number
  meanTimeToRespondMinutes: number
}

export interface DistributionItem {
  label: string
  value: number
}

export interface TrendPoint {
  label: string
  value: number
}

export interface EntityRecord {
  id: string
  type: 'User' | 'Host' | 'IP' | 'Process' | 'Asset'
  name: string
  currentRisk: number
  relatedAlerts: number
  incidents: number
  riskTrend: number[]
  tags: string[]
  behaviorSummary: string
}

export interface CaseRecord {
  id: string
  title: string
  owner: string
  priority: 'P1' | 'P2' | 'P3' | 'P4'
  status: CaseStatus
  relatedAlertIds: string[]
  notes: string[]
  evidence: string[]
  resolutionSummary: string
  timeline: Array<{ time: string; action: string; actor: string }>
}

export interface PlaybookRecommendation {
  id: string
  alertId: string
  action: string
  rationale: string
  riskIfNoAction: string
  confidence: number
  preconditions: string[]
  safeAlternatives: string[]
}

export interface ApprovalRecord {
  id: string
  actionId: string
  sensitiveAction: string
  requestedBy: string
  approver: string
  status: 'Pending' | 'Approved' | 'Rejected'
  justification: string
  requestedAt: string
  decidedAt: string
}

export interface ActionExecutionRecord {
  id: string
  action: string
  alertId: string
  approvedBy: string
  executedAt: string
  result: 'Success' | 'Failed' | 'Pending'
  failureReason: string
  rollbackAvailable: boolean
  systemsTouched: string[]
}

export interface AssetContextRecord {
  id: string
  assetName: string
  criticality: 'Low' | 'Medium' | 'High' | 'Mission Critical'
  crownJewel: boolean
  internetFacing: boolean
  privilegedAccount: boolean
  department: string
  businessUnit: string
  cvss: number
  threatIntel: string
}

export interface MitreCoverageRecord {
  techniqueId: string
  technique: string
  tactic: string
  alerts: number
}

export interface AuditRecord {
  time: string
  actor: string
  action: string
  target: string
  outcome: string
}

export interface NotificationRecord {
  id: string
  type: 'Critical Popup' | 'Escalation' | 'SLA Warning'
  message: string
  owner: string
  dueInMinutes: number
}

export interface AnalyticsMetric {
  label: string
  value: string
  trend: string
}

export interface ModelHealthRecord {
  metric: string
  value: string
  status: 'Healthy' | 'Warning' | 'Critical'
}

export interface DataSourceHealthRecord {
  source: string
  connected: boolean
  activeEndpoints: number
  lastLogReceived: string
  backlog: number
  warning: string
}

export interface RoleRecord {
  role: string
  permissions: string[]
}

export interface EvidenceBundle {
  id: string
  caseId: string
  includes: string[]
}