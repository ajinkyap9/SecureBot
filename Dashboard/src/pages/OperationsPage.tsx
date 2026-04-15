import { useMemo, useState } from 'react'
import {
  assetContext,
  dataSourceHealth,
  mitreCoverage,
  modelHealth,
} from '../data/mockData'
import { useSoc } from '../context/SocContext'
import {
  BarItem,
  HealthTag,
  InfoTile,
  SeverityBadge,
} from '../components/ui/dashboardPrimitives'
import {
  runDetectionOnly,
  runRiskAndDescription,
  type AlertInputPayload,
  type DetectionOnlyResponse,
} from '../services/backendApi'
import type { TimelineEvent } from '../types'

const entityTabs = ['User', 'Host', 'IP', 'Process', 'Asset'] as const

const defaultPayloadJson = JSON.stringify(
  {
    alert_id: 'ALRT-LIVE-9001',
    source: 'wazuh',
    ip: '10.42.14.19',
    process: 'powershell.exe',
    command: 'powershell -enc SQBmACgAJABQAFMAVgBlAHIAcwBpAG8AbgBUAGEAYgBsAGUALgBQAFMAVgBlAHIAcwBpAG8AbgApAA==',
    timestamp: '2025-01-15T09:14:55Z',
    asset_criticality: 'high',
    privileged_account_flag: 1,
    sensitive_data_flag: 1,
    spread_count_hosts: 2,
    ueba_score: 0.82,
    lateral_movement_flag: 1,
  },
  null,
  2,
)

interface LogModalState {
  title: string
  subtitle: string
  payload: string
  tags: string[]
}

export function OperationsPage() {
  const {
    selectedAlert,
    selectedEntityTab,
    setSelectedEntityTab,
    activeEntityRecords,
  } = useSoc()

  const [livePayloadJson, setLivePayloadJson] = useState(defaultPayloadJson)
  const [liveDetectionResult, setLiveDetectionResult] = useState<DetectionOnlyResponse | null>(null)
  const [liveRiskResult, setLiveRiskResult] = useState<DetectionOnlyResponse | null>(null)
  const [backendStatus, setBackendStatus] = useState<'idle' | 'detection' | 'risk'>('idle')
  const [backendError, setBackendError] = useState('')
  const [logModal, setLogModal] = useState<LogModalState | null>(null)

  const parseLivePayload = (): AlertInputPayload => {
    const parsed = JSON.parse(livePayloadJson) as AlertInputPayload
    if (!parsed.alert_id || !parsed.source || !parsed.timestamp) {
      throw new Error('Payload requires alert_id, source, and timestamp.')
    }
    return parsed
  }

  const runLiveDetection = async () => {
    setBackendStatus('detection')
    setBackendError('')
    try {
      const payload = parseLivePayload()
      const response = await runDetectionOnly(payload)
      setLiveDetectionResult(response)
    } catch (error) {
      setBackendError(error instanceof Error ? error.message : 'Detection request failed')
    } finally {
      setBackendStatus('idle')
    }
  }

  const runLiveRiskAnalysis = async () => {
    setBackendStatus('risk')
    setBackendError('')
    try {
      const payload = parseLivePayload()
      const response = await runRiskAndDescription(payload)
      setLiveRiskResult(response)
    } catch (error) {
      setBackendError(error instanceof Error ? error.message : 'Risk analysis request failed')
    } finally {
      setBackendStatus('idle')
    }
  }

  const liveModeLabel = useMemo(() => {
    if (backendStatus === 'detection') {
      return 'Running detection...'
    }
    if (backendStatus === 'risk') {
      return 'Running risk analysis...'
    }
    return 'Ready'
  }, [backendStatus])

  const mitreByTactic = mitreCoverage.reduce<Record<string, number>>((accumulator, row) => {
    accumulator[row.tactic] = (accumulator[row.tactic] ?? 0) + row.alerts
    return accumulator
  }, {})

  const openRawAlertLog = () => {
    if (!selectedAlert) {
      return
    }

    setLogModal({
      title: `Raw log payload ${selectedAlert.id}`,
      subtitle: `${selectedAlert.source} | ${selectedAlert.timestamp}`,
      payload: selectedAlert.rawEvent,
      tags: [selectedAlert.host, selectedAlert.user, selectedAlert.ip, selectedAlert.mitreTechnique],
    })
  }

  const openTimelineLog = (event: TimelineEvent) => {
    const payload = JSON.stringify(
      {
        timeline_event: event.event,
        source: event.source,
        time: event.time,
        user: event.user,
        host: event.host,
        ip: event.ip,
        pivot: event.pivot,
        linked_alert: selectedAlert?.id ?? null,
      },
      null,
      2,
    )

    setLogModal({
      title: `Timeline log ${event.time}`,
      subtitle: event.event,
      payload,
      tags: [event.source, event.pivot, event.user],
    })
  }

  const openSourceLog = (source: (typeof dataSourceHealth)[number]) => {
    const payload = JSON.stringify(
      {
        source: source.source,
        connected: source.connected,
        active_endpoints: source.activeEndpoints,
        last_log_received: source.lastLogReceived,
        queue_backlog: source.backlog,
        warning: source.warning,
      },
      null,
      2,
    )

    setLogModal({
      title: `Source log snapshot ${source.source}`,
      subtitle: `Backlog ${source.backlog} | Endpoints ${source.activeEndpoints}`,
      payload,
      tags: [source.connected ? 'connected' : 'disconnected', source.source],
    })
  }

  return (
    <>
      <section className="panel animate-rise">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="panel-title">UEBA analysis console</p>
            <p className="panel-subtitle">
              Behavior analytics and risk scoring only. No automated response actions are triggered here.
            </p>
          </div>
          <span className="chip">{liveModeLabel}</span>
        </div>

        <div className="mt-4 grid gap-4 xl:grid-cols-12">
          <div className="xl:col-span-6">
            <p className="text-xs uppercase tracking-[0.1em] text-slate-300">Alert JSON payload</p>
            <textarea
              value={livePayloadJson}
              onChange={(event) => setLivePayloadJson(event.target.value)}
              className="mt-2 h-64 w-full rounded-xl border border-slate-700/70 bg-slate-950/75 p-3 font-mono text-xs text-slate-100 outline-none"
            />
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                onClick={runLiveDetection}
                disabled={backendStatus !== 'idle'}
                className="rounded-lg border border-cyan-300/35 bg-cyan-400/15 px-3 py-2 text-xs font-semibold text-cyan-100 transition hover:bg-cyan-400/30 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Run detection
              </button>
              <button
                onClick={runLiveRiskAnalysis}
                disabled={backendStatus !== 'idle'}
                className="rounded-lg border border-emerald-300/35 bg-emerald-400/15 px-3 py-2 text-xs font-semibold text-emerald-100 transition hover:bg-emerald-400/30 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Run risk analysis
              </button>
            </div>
            {backendError ? (
              <p className="mt-3 rounded-lg border border-red-300/35 bg-red-500/10 px-3 py-2 text-xs text-red-100">
                {backendError}
              </p>
            ) : null}
          </div>

          <div className="space-y-3 xl:col-span-3">
            <div className="rounded-xl border border-slate-700/75 bg-slate-900/55 p-3 text-xs">
              <p className="text-slate-300">Latest detection mode</p>
              <p className="mt-1 font-mono text-cyan-100">{liveDetectionResult?.mode ?? '-'}</p>
              <p className="mt-2 text-slate-300">Should run risk</p>
              <p className="mt-1 font-semibold text-slate-100">
                {liveDetectionResult?.detection_section.should_run_risk ? 'Yes' : 'No'}
              </p>
              <p className="mt-2 text-slate-300">Potential reasons</p>
              <p className="mt-1 text-slate-200">
                {(liveDetectionResult?.detection_section.potential_reasons ?? []).join(', ') || '-'}
              </p>
            </div>

            <div className="rounded-xl border border-slate-700/75 bg-slate-900/55 p-3 text-xs">
              <p className="text-slate-300">Risk label</p>
              <p className="mt-1 font-semibold text-slate-100">
                {String(liveRiskResult?.risk_section?.risk_label ?? '-')}
              </p>
              <p className="mt-2 text-slate-300">Action mode from backend</p>
              <p className="mt-1 font-mono text-amber-100">
                {String(liveRiskResult?.decision_section?.action_mode ?? 'analysis_only')}
              </p>
              <p className="mt-2 text-slate-300">Model confidence</p>
              <p className="mt-1 text-slate-100">
                {String(liveRiskResult?.detection_section.intel_summary.confidence ?? '-')}
              </p>
            </div>
          </div>

          <div className="xl:col-span-3">
            <div className="rounded-xl border border-cyan-300/35 bg-cyan-400/10 p-3 text-xs text-cyan-100">
              <p className="font-semibold">UEBA mode enabled</p>
              <p className="mt-2">
                This view is configured for analysis and risk scoring. Response execution panels are intentionally hidden.
              </p>
            </div>

            {selectedAlert ? (
              <div className="mt-3 rounded-xl border border-slate-700/75 bg-slate-900/55 p-3 text-xs">
                <p className="text-slate-300">Current investigation anchor</p>
                <p className="mt-1 font-mono text-cyan-100">{selectedAlert.id}</p>
                <p className="mt-1 text-slate-200">{selectedAlert.summary}</p>
                <button
                  onClick={openRawAlertLog}
                  className="mt-3 w-full rounded-lg border border-cyan-300/40 bg-cyan-400/15 px-3 py-2 text-xs font-semibold text-cyan-100 transition hover:bg-cyan-400/30"
                >
                  Open raw log popup
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-12">
        <article className="panel animate-rise xl:col-span-5">
          <p className="panel-title">Entity-centric risk posture</p>
          <p className="panel-subtitle">Pivot by User, Host, IP, Process, or Asset to inspect behavior drift.</p>

          <div className="mt-3 flex flex-wrap gap-2">
            {entityTabs.map((tab) => (
              <button
                key={tab}
                onClick={() => setSelectedEntityTab(tab)}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${selectedEntityTab === tab ? 'bg-cyan-400/20 text-cyan-100' : 'bg-slate-800/70 text-slate-300'}`}
              >
                {tab} view
              </button>
            ))}
          </div>

          <div className="mt-4 space-y-3">
            {activeEntityRecords.map((entity) => (
              <div key={entity.id} className="rounded-xl border border-slate-700/75 bg-slate-900/55 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold text-slate-100">{entity.name}</p>
                    <p className="text-xs text-slate-300">{entity.behaviorSummary}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-400">Current risk</p>
                    <p className="font-mono text-lg text-cyan-200">{entity.currentRisk}</p>
                  </div>
                </div>

                <div className="mt-2 flex flex-wrap gap-2">
                  {entity.tags.map((tag) => (
                    <span key={tag} className="chip">
                      {tag}
                    </span>
                  ))}
                </div>

                <div className="mt-3 grid grid-cols-3 gap-3 text-xs">
                  <div className="rounded-lg border border-slate-700/70 bg-slate-950/40 px-2 py-1.5">
                    Alerts: <span className="font-semibold">{entity.relatedAlerts}</span>
                  </div>
                  <div className="rounded-lg border border-slate-700/70 bg-slate-950/40 px-2 py-1.5">
                    Incidents: <span className="font-semibold">{entity.incidents}</span>
                  </div>
                  <div className="rounded-lg border border-slate-700/70 bg-slate-950/40 px-2 py-1.5">
                    Trend: <span className="font-semibold">{entity.riskTrend[entity.riskTrend.length - 1]}</span>
                  </div>
                </div>

                <div className="mt-2 grid h-10 grid-cols-6 items-end gap-1">
                  {entity.riskTrend.map((value, index) => (
                    <div
                      key={`${entity.id}-${index}`}
                      className="rounded-t bg-gradient-to-t from-emerald-400/80 to-cyan-300"
                      style={{ height: `${Math.max(12, value)}%` }}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="panel animate-rise xl:col-span-4">
          <p className="panel-title">Alert risk anatomy</p>
          <p className="panel-subtitle">Feature evidence and weighted risk factors for the selected alert.</p>

          {selectedAlert ? (
            <div className="mt-4 space-y-3">
              <div className="rounded-xl border border-slate-700/75 bg-slate-900/55 p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-semibold text-slate-100">{selectedAlert.id}</p>
                  <SeverityBadge severity={selectedAlert.severity} />
                </div>
                <p className="mt-1 text-sm text-cyan-100">{selectedAlert.detectionLabel}</p>
                <p className="mt-1 text-xs text-slate-300">{selectedAlert.summary}</p>

                <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                  <InfoTile label="Risk score" value={selectedAlert.riskScore.toFixed(2)} />
                  <InfoTile label="Anomaly score" value={selectedAlert.anomalyScore.toFixed(2)} />
                  <InfoTile label="Confidence" value={`${Math.round(selectedAlert.modelScores.confidence * 100)}%`} />
                </div>
              </div>

              <div className="rounded-xl border border-slate-700/75 bg-slate-900/55 p-3">
                <p className="text-xs uppercase tracking-[0.12em] text-slate-300">Explainability</p>
                <div className="mt-2 space-y-2">
                  {selectedAlert.explainability.map((item) => (
                    <div key={item.feature} className="rounded-lg border border-slate-700/70 bg-slate-950/40 p-2 text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-cyan-100">{item.feature}</span>
                        <span className="font-mono text-slate-200">{(item.impact * 100).toFixed(0)}%</span>
                      </div>
                      <p className="mt-1 text-slate-300">{item.reason}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-slate-700/75 bg-slate-900/55 p-3">
                <p className="text-xs uppercase tracking-[0.12em] text-slate-300">Risk factor weighting</p>
                <div className="mt-2 space-y-2 text-xs">
                  {selectedAlert.riskFactors.map((factor) => (
                    <div key={factor.factor} className="rounded-lg border border-slate-700/70 bg-slate-950/40 p-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-slate-100">{factor.factor}</span>
                        <span className="font-mono text-cyan-100">{factor.weight}%</span>
                      </div>
                      <p className="mt-1 text-slate-300">{factor.detail}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-300">Select an alert in overview to inspect risk anatomy.</p>
          )}
        </article>

        <article className="panel animate-rise xl:col-span-3">
          <p className="panel-title">Source health and incoming logs</p>
          <p className="panel-subtitle">See exactly which source logs are arriving and open them in popup view.</p>

          <div className="mt-4 space-y-2">
            {dataSourceHealth.map((source) => (
              <div key={source.source} className="rounded-lg border border-slate-700/70 bg-slate-900/55 p-2.5 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm text-slate-100">{source.source}</p>
                  <span
                    className={`rounded-full px-2 py-0.5 font-semibold ${source.connected ? 'bg-emerald-500/20 text-emerald-100' : 'bg-red-500/20 text-red-100'}`}
                  >
                    {source.connected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
                <p className="mt-1 text-slate-300">Last log received: {source.lastLogReceived}</p>
                <p className="text-slate-300">Queue backlog: {source.backlog}</p>
                <p className="text-amber-200">{source.warning}</p>
                <button
                  onClick={() => openSourceLog(source)}
                  className="mt-2 w-full rounded-md border border-cyan-300/35 bg-cyan-400/10 px-2 py-1 text-xs font-semibold text-cyan-100 transition hover:bg-cyan-400/25"
                >
                  Open source log popup
                </button>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="grid gap-4 xl:grid-cols-12">
        <article className="panel animate-rise xl:col-span-5">
          <p className="panel-title">Investigation timeline with log popup</p>
          <p className="panel-subtitle">Click any event to open the exact timeline log payload.</p>

          {selectedAlert ? (
            <div className="mt-4 space-y-2">
              {selectedAlert.relatedEvents.map((event) => (
                <button
                  key={`${event.time}-${event.event}`}
                  onClick={() => openTimelineLog(event)}
                  className="w-full rounded-xl border border-slate-700/70 bg-slate-900/55 p-3 text-left transition hover:border-cyan-300/45 hover:bg-slate-900/80"
                >
                  <p className="font-mono text-xs text-cyan-100">{event.time}</p>
                  <p className="mt-1 text-sm text-slate-100">{event.event}</p>
                  <p className="mt-1 text-xs text-slate-300">
                    {event.source} | {event.user} | {event.host} | {event.ip}
                  </p>
                  <span className="mt-2 inline-flex rounded-full border border-slate-600/70 px-2 py-0.5 text-[10px] uppercase tracking-[0.1em] text-slate-300">
                    Pivot {event.pivot}
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-300">Select an alert in overview to inspect event logs.</p>
          )}
        </article>

        <article className="panel animate-rise xl:col-span-4">
          <p className="panel-title">MITRE tactic pressure</p>
          <p className="panel-subtitle">Tactic-level concentration to prioritize analysis depth.</p>

          <div className="mt-4 space-y-2">
            {Object.entries(mitreByTactic).map(([tactic, count]) => (
              <BarItem key={tactic} label={tactic} value={count} maxValue={45} mode="source" />
            ))}
          </div>

          <div className="mt-5 border-t border-slate-700/70 pt-4">
            <p className="panel-title">Model health</p>
            <p className="panel-subtitle">Pipeline quality checks for trustworthy risk analytics.</p>
            <div className="mt-3 space-y-2">
              {modelHealth.map((item) => (
                <div key={item.metric} className="rounded-lg border border-slate-700/70 bg-slate-900/55 p-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm text-slate-100">{item.metric}</p>
                    <HealthTag status={item.status} />
                  </div>
                  <p className="mt-1 text-xs text-slate-300">{item.value}</p>
                </div>
              ))}
            </div>
          </div>
        </article>

        <article className="panel animate-rise xl:col-span-3">
          <p className="panel-title">Asset risk context</p>
          <p className="panel-subtitle">Criticality and exposure context that influences UEBA risk score.</p>

          <div className="mt-4 space-y-2">
            {assetContext.slice(0, 4).map((asset) => (
              <div key={asset.id} className="rounded-lg border border-slate-700/70 bg-slate-900/55 p-2.5 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm text-slate-100">{asset.assetName}</p>
                  <span className="chip">{asset.criticality}</span>
                </div>
                <p className="mt-1 text-slate-300">Department: {asset.department}</p>
                <p className="text-slate-300">CVSS: {asset.cvss.toFixed(1)}</p>
                <p className="text-slate-300">Threat intel: {asset.threatIntel}</p>
              </div>
            ))}
          </div>
        </article>
      </section>

      {logModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 p-4 backdrop-blur-sm">
          <div className="w-full max-w-3xl rounded-2xl border border-cyan-300/35 bg-slate-950/95 p-4 shadow-glow">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.14em] text-cyan-200">{logModal.title}</p>
                <p className="mt-1 text-xs text-slate-300">{logModal.subtitle}</p>
              </div>
              <button
                onClick={() => setLogModal(null)}
                className="rounded-md border border-slate-500/60 bg-slate-800/80 px-2 py-1 text-xs text-slate-200"
              >
                Close
              </button>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {logModal.tags.map((tag) => (
                <span key={`${logModal.title}-${tag}`} className="chip">
                  {tag}
                </span>
              ))}
            </div>

            <pre className="mt-4 max-h-[55vh] overflow-auto rounded-xl border border-slate-700/70 bg-slate-900/65 p-3 font-mono text-xs text-cyan-100">
              {logModal.payload}
            </pre>
          </div>
        </div>
      ) : null}
    </>
  )
}
