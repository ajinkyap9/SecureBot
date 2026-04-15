import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from 'react'
import {
  alerts,
  entityRecords,
  initialActionExecutions,
  initialApprovals,
  initialCases,
  playbookRecommendations,
  roleAccess,
} from '../data/mockData'
import type {
  AlertStatus,
  ApprovalRecord,
  CaseRecord,
  EntityRecord,
  Severity,
} from '../types'

export type TrendWindow = '24h' | '7d'
export type EntityTab = EntityRecord['type']
export type Decision = 'Approved' | 'Rejected'

export interface QueueFilters {
  timeRange: '24h' | '7d' | '30d'
  severity: 'All' | Severity
  asset: string
  user: string
  alertType: string
  privileged: 'All' | 'Yes' | 'No'
  crownJewel: 'All' | 'Yes' | 'No'
  status: 'All' | AlertStatus
  source: 'All' | string
}

export interface SearchResult {
  id: string
  kind: 'Alert' | 'Case'
  title: string
  subtitle: string
}

interface SocContextValue {
  trendWindow: TrendWindow
  setTrendWindow: (value: TrendWindow) => void
  searchTerm: string
  setSearchTerm: (value: string) => void
  selectedRole: string
  setSelectedRole: (value: string) => void
  selectedEntityTab: EntityTab
  setSelectedEntityTab: (value: EntityTab) => void
  selectedAlertId: string
  setSelectedAlertId: (value: string) => void
  queueFilters: QueueFilters
  setQueueFilters: Dispatch<SetStateAction<QueueFilters>>
  queueAssets: string[]
  queueUsers: string[]
  queueTypes: string[]
  queueSources: string[]
  filteredAlerts: typeof alerts
  selectedAlert: (typeof alerts)[number] | null
  selectedRecommendations: typeof playbookRecommendations
  activeEntityRecords: EntityRecord[]
  caseRecords: CaseRecord[]
  approvals: ApprovalRecord[]
  actionExecutions: typeof initialActionExecutions
  justifications: Record<string, string>
  setJustificationForApproval: (approvalId: string, value: string) => void
  searchResults: SearchResult[]
  activeRole: (typeof roleAccess)[number]
  totalRelatedAlerts: number
  toast: string
  dismissToast: () => void
  executeApprovalDecision: (approvalId: string, decision: Decision) => void
  requestAction: (actionId: string, actionName: string) => void
  createCaseFromAlert: () => void
  applyPivot: (target: 'user' | 'host' | 'ip' | 'related', value?: string) => void
}

const severityOrder: Record<Severity, number> = {
  Critical: 4,
  High: 3,
  Medium: 2,
  Low: 1,
}

const defaultFilters: QueueFilters = {
  timeRange: '24h',
  severity: 'All',
  asset: 'All',
  user: 'All',
  alertType: 'All',
  privileged: 'All',
  crownJewel: 'All',
  status: 'All',
  source: 'All',
}

const SocContext = createContext<SocContextValue | undefined>(undefined)

export function SocProvider({ children }: { children: ReactNode }) {
  const [trendWindow, setTrendWindow] = useState<TrendWindow>('24h')
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedRole, setSelectedRole] = useState('SOC Analyst')
  const [selectedEntityTab, setSelectedEntityTab] = useState<EntityTab>('User')
  const [selectedAlertId, setSelectedAlertId] = useState(alerts[0]?.id ?? '')
  const [queueFilters, setQueueFilters] = useState<QueueFilters>(defaultFilters)
  const [caseRecords, setCaseRecords] = useState<CaseRecord[]>(initialCases)
  const [approvals, setApprovals] = useState(initialApprovals)
  const [actionExecutions, setActionExecutions] = useState(initialActionExecutions)
  const [justifications, setJustifications] = useState<Record<string, string>>({})
  const [toast, setToast] = useState('')

  const queueAssets = useMemo(() => uniqueValues(alerts.map((alert) => alert.host)), [])
  const queueUsers = useMemo(() => uniqueValues(alerts.map((alert) => alert.user)), [])
  const queueTypes = useMemo(() => uniqueValues(alerts.map((alert) => alert.alertType)), [])
  const queueSources = useMemo(() => uniqueValues(alerts.map((alert) => alert.source)), [])

  const filteredAlerts = useMemo(() => {
    return alerts
      .filter((alert) => {
        if (queueFilters.timeRange !== '30d') {
          const lookbackHours = queueFilters.timeRange === '24h' ? 24 : 24 * 7
          const parsedTimestamp = new Date(alert.timestamp.replace(' ', 'T'))
          if (!Number.isNaN(parsedTimestamp.getTime())) {
            const ageInHours = (Date.now() - parsedTimestamp.getTime()) / (1000 * 60 * 60)
            if (ageInHours > lookbackHours) {
              return false
            }
          }
        }

        if (queueFilters.severity !== 'All' && alert.severity !== queueFilters.severity) {
          return false
        }
        if (queueFilters.asset !== 'All' && alert.host !== queueFilters.asset) {
          return false
        }
        if (queueFilters.user !== 'All' && alert.user !== queueFilters.user) {
          return false
        }
        if (queueFilters.alertType !== 'All' && alert.alertType !== queueFilters.alertType) {
          return false
        }
        if (queueFilters.privileged === 'Yes' && !alert.privileged) {
          return false
        }
        if (queueFilters.privileged === 'No' && alert.privileged) {
          return false
        }
        if (queueFilters.crownJewel === 'Yes' && !alert.crownJewel) {
          return false
        }
        if (queueFilters.crownJewel === 'No' && alert.crownJewel) {
          return false
        }
        if (queueFilters.status !== 'All' && alert.status !== queueFilters.status) {
          return false
        }
        if (queueFilters.source !== 'All' && alert.source !== queueFilters.source) {
          return false
        }
        return true
      })
      .sort((a, b) => {
        const severityDelta = severityOrder[b.severity] - severityOrder[a.severity]
        if (severityDelta !== 0) {
          return severityDelta
        }
        return b.riskScore - a.riskScore
      })
  }, [queueFilters])

  useEffect(() => {
    if (!filteredAlerts.length) {
      return
    }
    const stillVisible = filteredAlerts.some((alert) => alert.id === selectedAlertId)
    if (!stillVisible) {
      setSelectedAlertId(filteredAlerts[0].id)
    }
  }, [filteredAlerts, selectedAlertId])

  const selectedAlert = useMemo(
    () => alerts.find((alert) => alert.id === selectedAlertId) ?? filteredAlerts[0] ?? null,
    [selectedAlertId, filteredAlerts],
  )

  const selectedRecommendations = useMemo(() => {
    if (!selectedAlert) {
      return []
    }
    return playbookRecommendations.filter((recommendation) => recommendation.alertId === selectedAlert.id)
  }, [selectedAlert])

  const activeEntityRecords = useMemo(
    () => entityRecords.filter((record) => record.type === selectedEntityTab),
    [selectedEntityTab],
  )

  const searchResults = useMemo(() => {
    const query = searchTerm.trim().toLowerCase()
    if (!query) {
      return []
    }

    const alertMatches: SearchResult[] = alerts
      .filter((alert) =>
        [alert.id, alert.user, alert.host, alert.ip, alert.fileHash, alert.process].some((field) =>
          field.toLowerCase().includes(query),
        ),
      )
      .map((alert) => ({
        id: alert.id,
        kind: 'Alert',
        title: alert.id,
        subtitle: `${alert.user} | ${alert.host} | ${alert.ip}`,
      }))

    const caseMatches: SearchResult[] = caseRecords
      .filter((record) =>
        [record.id, record.title, record.owner, ...record.relatedAlertIds].some((field) =>
          field.toLowerCase().includes(query),
        ),
      )
      .map((record) => ({
        id: record.id,
        kind: 'Case',
        title: record.id,
        subtitle: `${record.status} | Owner: ${record.owner}`,
      }))

    return [...alertMatches, ...caseMatches].slice(0, 8)
  }, [searchTerm, caseRecords])

  const activeRole = roleAccess.find((role) => role.role === selectedRole) ?? roleAccess[0]

  const totalRelatedAlerts = caseRecords.reduce(
    (total, record) => total + record.relatedAlertIds.length,
    0,
  )

  const setJustificationForApproval = (approvalId: string, value: string) => {
    setJustifications((previous) => ({ ...previous, [approvalId]: value }))
  }

  const executeApprovalDecision = (approvalId: string, decision: Decision) => {
    const existingApproval = approvals.find((approval) => approval.id === approvalId)
    if (!existingApproval) {
      return
    }

    const justification = justifications[approvalId]?.trim() ?? ''
    const decidedAt = nowTimestamp()
    const updatedApproval: ApprovalRecord = {
      ...existingApproval,
      status: decision,
      approver: 'R. Iyer',
      justification: justification || `${decision} by approver`,
      decidedAt,
    }

    setApprovals((previous) =>
      previous.map((approval) => {
        if (approval.id !== approvalId) {
          return approval
        }
        return updatedApproval
      }),
    )

    if (decision === 'Approved') {
      setActionExecutions((previous) => [
        {
          id: `EXEC-${470 + previous.length + 1}`,
          action: updatedApproval.sensitiveAction,
          alertId: selectedAlert?.id ?? 'n/a',
          approvedBy: 'R. Iyer',
          executedAt: nowTimestamp(),
          result: 'Pending',
          failureReason: '-',
          rollbackAvailable: true,
          systemsTouched: selectedAlert ? [selectedAlert.host, selectedAlert.source] : ['orchestrator'],
        },
        ...previous,
      ])
    }

    setToast(`${approvalId} marked as ${decision}.`)
  }

  const requestAction = (actionId: string, actionName: string) => {
    setApprovals((previous) => [
      {
        id: `APR-${530 + previous.length + 1}`,
        actionId,
        sensitiveAction: actionName,
        requestedBy: 'SOC Analyst Queue',
        approver: 'Pending',
        status: 'Pending',
        justification: '',
        requestedAt: nowTimestamp(),
        decidedAt: '-',
      },
      ...previous,
    ])
    setToast(`Action request submitted: ${actionName}`)
  }

  const createCaseFromAlert = () => {
    if (!selectedAlert) {
      return
    }

    const caseId = `CASE-${790 + caseRecords.length + 1}`
    const newCase: CaseRecord = {
      id: caseId,
      title: `Investigation for ${selectedAlert.id}`,
      owner: 'SOC Queue',
      priority: selectedAlert.severity === 'Critical' ? 'P1' : 'P2',
      status: 'New',
      relatedAlertIds: [selectedAlert.id],
      notes: [`Case auto-created from alert ${selectedAlert.id}`],
      evidence: ['raw-event.json'],
      resolutionSummary: 'In progress.',
      timeline: [
        {
          time: nowTimestamp().slice(11, 16),
          action: `Case created from ${selectedAlert.id}`,
          actor: 'SecureBot SOC Agent',
        },
      ],
    }

    setCaseRecords((previous) => [newCase, ...previous])
    setToast(`Created ${caseId} from ${selectedAlert.id}`)
  }

  const applyPivot = (target: 'user' | 'host' | 'ip' | 'related', value?: string) => {
    if (!selectedAlert && !value) {
      return
    }

    if (target === 'related' && selectedAlert) {
      setQueueFilters((previous) => ({
        ...previous,
        user: selectedAlert.user,
        asset: selectedAlert.host,
      }))
      return
    }

    if (target === 'user' && selectedAlert) {
      setQueueFilters((previous) => ({ ...previous, user: value ?? selectedAlert.user }))
      return
    }

    if (target === 'host' && selectedAlert) {
      setQueueFilters((previous) => ({ ...previous, asset: value ?? selectedAlert.host }))
      return
    }

    if (target === 'ip' && selectedAlert) {
      setSearchTerm(value ?? selectedAlert.ip)
    }
  }

  const dismissToast = () => setToast('')

  const value: SocContextValue = {
    trendWindow,
    setTrendWindow,
    searchTerm,
    setSearchTerm,
    selectedRole,
    setSelectedRole,
    selectedEntityTab,
    setSelectedEntityTab,
    selectedAlertId,
    setSelectedAlertId,
    queueFilters,
    setQueueFilters,
    queueAssets,
    queueUsers,
    queueTypes,
    queueSources,
    filteredAlerts,
    selectedAlert,
    selectedRecommendations,
    activeEntityRecords,
    caseRecords,
    approvals,
    actionExecutions,
    justifications,
    setJustificationForApproval,
    searchResults,
    activeRole,
    totalRelatedAlerts,
    toast,
    dismissToast,
    executeApprovalDecision,
    requestAction,
    createCaseFromAlert,
    applyPivot,
  }

  return <SocContext.Provider value={value}>{children}</SocContext.Provider>
}

export function useSoc() {
  const context = useContext(SocContext)
  if (!context) {
    throw new Error('useSoc must be used inside SocProvider')
  }
  return context
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values))
}

function nowTimestamp() {
  const now = new Date()
  const year = now.getFullYear()
  const month = `${now.getMonth() + 1}`.padStart(2, '0')
  const day = `${now.getDate()}`.padStart(2, '0')
  const hour = `${now.getHours()}`.padStart(2, '0')
  const minute = `${now.getMinutes()}`.padStart(2, '0')
  const second = `${now.getSeconds()}`.padStart(2, '0')
  return `${year}-${month}-${day} ${hour}:${minute}:${second}`
}
