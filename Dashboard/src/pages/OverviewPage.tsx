import {
  alertsBySeverity,
  alertsBySource,
  overviewMetrics,
  trend24h,
  trend7d,
} from '../data/mockData'
import { useSoc } from '../context/SocContext'
import {
  BarItem,
  FilterSelect,
  MetricCard,
  ScoreCard,
  SeverityBadge,
  StatusBadge,
  TimelineRow,
} from '../components/ui/dashboardPrimitives'
import { confidenceBand, maxTrendValue } from '../utils/dashboard'

export function OverviewPage() {
  const {
    trendWindow,
    setTrendWindow,
    queueFilters,
    setQueueFilters,
    queueAssets,
    queueUsers,
    queueTypes,
    queueSources,
    filteredAlerts,
    selectedAlert,
    selectedAlertId,
    setSelectedAlertId,
    selectedRecommendations,
    searchResults,
    applyPivot,
  } = useSoc()

  const trendData = trendWindow === '24h' ? trend24h : trend7d

  return (
    <>
      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <MetricCard
          label="Total events ingested"
          value={overviewMetrics.totalEventsIngested.toLocaleString()}
          hint="Live stream from all telemetry"
          tone="sky"
        />
        <MetricCard
          label="Total alerts generated"
          value={overviewMetrics.totalAlertsGenerated.toLocaleString()}
          hint="Model + rule detections"
          tone="indigo"
        />
        <MetricCard
          label="Open incidents"
          value={overviewMetrics.openIncidents.toString()}
          hint="Cases requiring action"
          tone="teal"
        />
        <MetricCard
          label="High/Critical alerts"
          value={overviewMetrics.highCriticalAlerts.toString()}
          hint="Priority queue right now"
          tone="red"
        />
        <MetricCard
          label="Mean time to detect"
          value={`${overviewMetrics.meanTimeToDetectMinutes} min`}
          hint="From event to alert"
          tone="emerald"
        />
        <MetricCard
          label="Mean time to risk classification"
          value={`${overviewMetrics.meanTimeToRespondMinutes} min`}
          hint="From alert to final risk label"
          tone="amber"
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-12">
        <article className="panel animate-rise lg:col-span-6">
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="panel-title">Alert trend</p>
              <p className="panel-subtitle">Last 24h / 7d operational pulse</p>
            </div>
            <div className="rounded-xl border border-slate-700/60 bg-slate-900/60 p-1 text-xs">
              <button
                onClick={() => setTrendWindow('24h')}
                className={`rounded-lg px-3 py-1.5 ${trendWindow === '24h' ? 'bg-sky-400/20 text-sky-100' : 'text-slate-300'}`}
              >
                24h
              </button>
              <button
                onClick={() => setTrendWindow('7d')}
                className={`rounded-lg px-3 py-1.5 ${trendWindow === '7d' ? 'bg-sky-400/20 text-sky-100' : 'text-slate-300'}`}
              >
                7d
              </button>
            </div>
          </div>
          <div className="mt-4 grid h-44 grid-cols-8 items-end gap-2 rounded-xl border border-slate-800/80 bg-slate-900/55 p-3">
            {trendData.map((point) => (
              <div key={point.label} className="flex h-full flex-col justify-end">
                <div
                  className="rounded-t-md bg-gradient-to-t from-blue-500 to-cyan-300/90"
                  style={{ height: `${Math.max(14, (point.value / maxTrendValue(trendData)) * 100)}%` }}
                />
                <p className="mt-2 text-center font-mono text-[11px] text-slate-300">{point.label}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="panel animate-rise lg:col-span-3">
          <p className="panel-title">Alerts by severity</p>
          <div className="mt-3 space-y-3">
            {alertsBySeverity.map((item) => (
              <BarItem
                key={item.label}
                label={item.label}
                value={item.value}
                maxValue={alertsBySeverity[alertsBySeverity.length - 1].value}
                mode="severity"
              />
            ))}
          </div>
        </article>

        <article className="panel animate-rise lg:col-span-3">
          <p className="panel-title">Alerts by source</p>
          <div className="mt-3 space-y-3">
            {alertsBySource.map((item) => (
              <BarItem
                key={item.label}
                label={item.label}
                value={item.value}
                maxValue={alertsBySource[0].value}
                mode="source"
              />
            ))}
          </div>
        </article>
      </section>

      <section className="panel animate-rise">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="panel-title">Alert queue / triage panel</p>
            <p className="panel-subtitle">
              Filterable queue with anomaly and risk context, plus MITRE mapping for analyst pivots.
            </p>
          </div>
        </div>

        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-5 xl:grid-cols-9">
          <FilterSelect
            label="Time range"
            value={queueFilters.timeRange}
            options={['24h', '7d', '30d']}
            onChange={(value) => setQueueFilters((previous) => ({ ...previous, timeRange: value as typeof queueFilters.timeRange }))}
          />
          <FilterSelect
            label="Severity"
            value={queueFilters.severity}
            options={['All', 'Critical', 'High', 'Medium', 'Low']}
            onChange={(value) => setQueueFilters((previous) => ({ ...previous, severity: value as typeof queueFilters.severity }))}
          />
          <FilterSelect
            label="Asset"
            value={queueFilters.asset}
            options={['All', ...queueAssets]}
            onChange={(value) => setQueueFilters((previous) => ({ ...previous, asset: value }))}
          />
          <FilterSelect
            label="User"
            value={queueFilters.user}
            options={['All', ...queueUsers]}
            onChange={(value) => setQueueFilters((previous) => ({ ...previous, user: value }))}
          />
          <FilterSelect
            label="Alert type"
            value={queueFilters.alertType}
            options={['All', ...queueTypes]}
            onChange={(value) => setQueueFilters((previous) => ({ ...previous, alertType: value }))}
          />
          <FilterSelect
            label="Privileged account"
            value={queueFilters.privileged}
            options={['All', 'Yes', 'No']}
            onChange={(value) => setQueueFilters((previous) => ({ ...previous, privileged: value as typeof queueFilters.privileged }))}
          />
          <FilterSelect
            label="Crown jewel asset"
            value={queueFilters.crownJewel}
            options={['All', 'Yes', 'No']}
            onChange={(value) => setQueueFilters((previous) => ({ ...previous, crownJewel: value as typeof queueFilters.crownJewel }))}
          />
          <FilterSelect
            label="Status"
            value={queueFilters.status}
            options={['All', 'New', 'Under Review', 'Escalated', 'Resolved']}
            onChange={(value) => setQueueFilters((previous) => ({ ...previous, status: value as typeof queueFilters.status }))}
          />
          <FilterSelect
            label="Source"
            value={queueFilters.source}
            options={['All', ...queueSources]}
            onChange={(value) => setQueueFilters((previous) => ({ ...previous, source: value }))}
          />
        </div>

        <div className="mt-4 overflow-x-auto rounded-xl border border-slate-800/80">
          <table className="min-w-[1320px] w-full border-collapse">
            <thead>
              <tr className="table-header">
                {[
                  'Alert ID',
                  'Timestamp',
                  'Host / endpoint',
                  'Username / account',
                  'Detection label',
                  'Combined anomaly score',
                  'Risk score',
                  'Severity',
                  'MITRE technique',
                  'Current status',
                  'Source',
                ].map((column) => (
                  <th key={column} className="px-3 py-2 font-semibold">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredAlerts.map((alert) => (
                <tr
                  key={alert.id}
                  className={`cursor-pointer transition hover:bg-slate-800/60 ${selectedAlertId === alert.id ? 'bg-sky-400/10' : 'bg-slate-950/35'}`}
                  onClick={() => setSelectedAlertId(alert.id)}
                >
                  <td className="table-cell font-mono text-xs text-cyan-200">{alert.id}</td>
                  <td className="table-cell font-mono text-xs">{alert.timestamp}</td>
                  <td className="table-cell">{alert.host}</td>
                  <td className="table-cell">{alert.user}</td>
                  <td className="table-cell">{alert.detectionLabel}</td>
                  <td className="table-cell font-mono">{alert.modelScores.combined.toFixed(2)}</td>
                  <td className="table-cell font-mono">{alert.riskScore.toFixed(2)}</td>
                  <td className="table-cell">
                    <SeverityBadge severity={alert.severity} />
                  </td>
                  <td className="table-cell font-mono text-xs">
                    {alert.mitreTechnique} / {alert.mitreTactic}
                  </td>
                  <td className="table-cell">
                    <StatusBadge status={alert.status} />
                  </td>
                  <td className="table-cell">{alert.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {selectedAlert ? (
        <section className="grid gap-4 xl:grid-cols-12">
          <article className="panel animate-rise xl:col-span-5">
            <p className="panel-title">Alert detail page</p>
            <p className="panel-subtitle">Investigation depth with model features, scores, and contextual recommendation.</p>

            <div className="mt-4 space-y-4">
              <div className="rounded-xl border border-slate-800/90 bg-slate-900/70 p-3">
                <h3 className="text-base font-semibold text-cyan-100">{selectedAlert.summary}</h3>
                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  <span className="chip">{selectedAlert.id}</span>
                  <span className="chip">{selectedAlert.source}</span>
                  <span className="chip">{selectedAlert.mitreTechnique}</span>
                  <span className="chip">Risk {selectedAlert.riskScore.toFixed(2)}</span>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <ScoreCard title="AE score" value={selectedAlert.modelScores.ae} />
                <ScoreCard title="IF score" value={selectedAlert.modelScores.iforest} />
                <ScoreCard title="Combined detection" value={selectedAlert.modelScores.combined} />
                <ScoreCard title="XGBoost risk" value={selectedAlert.modelScores.xgboostRisk} />
              </div>

              <div className="rounded-xl border border-slate-800/90 bg-slate-900/70 p-3">
                <p className="text-xs uppercase tracking-[0.14em] text-slate-300">Raw event details</p>
                <pre className="mt-2 overflow-x-auto whitespace-pre-wrap rounded-lg bg-slate-950/80 p-3 font-mono text-xs text-cyan-100">
                  {selectedAlert.rawEvent}
                </pre>
              </div>

              <div className="rounded-xl border border-slate-800/90 bg-slate-900/70 p-3">
                <p className="text-xs uppercase tracking-[0.14em] text-slate-300">Parsed features used by model</p>
                <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-2">
                  {selectedAlert.parsedFeatures.map((feature) => (
                    <div
                      key={feature.key}
                      className="rounded-lg border border-slate-700/80 bg-slate-950/50 px-2 py-1.5 text-xs"
                    >
                      <span className="font-mono text-sky-100">{feature.key}</span>
                      <span className="float-right font-mono text-slate-300">{feature.value}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-red-300/30 bg-red-500/10 p-3">
                <p className="text-xs uppercase tracking-[0.14em] text-red-200">Risk impact note</p>
                <p className="mt-2 text-sm text-red-100">{selectedAlert.recommendedNextStep}</p>
              </div>
            </div>
          </article>

          <article className="panel animate-rise xl:col-span-3">
            <p className="panel-title">Explainability panel</p>
            <p className="panel-subtitle">SHAP-style feature impacts and score interpretation.</p>

            <div className="mt-4 space-y-4">
              <div>
                <p className="text-xs uppercase tracking-[0.14em] text-slate-300">Top contributing features</p>
                <div className="mt-2 space-y-2">
                  {selectedAlert.explainability.map((item) => (
                    <div key={item.feature} className="rounded-lg border border-slate-700/70 bg-slate-900/50 p-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-mono text-cyan-100">{item.feature}</span>
                        <span className="font-mono">{(item.impact * 100).toFixed(0)}%</span>
                      </div>
                      <div className="mt-1 h-1.5 rounded-full bg-slate-700">
                        <div
                          className="h-1.5 rounded-full bg-gradient-to-r from-cyan-300 to-blue-500"
                          style={{ width: `${Math.max(item.impact * 100, 8)}%` }}
                        />
                      </div>
                      <p className="mt-1 text-xs text-slate-300">{item.reason}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 p-3">
                <p className="text-xs uppercase tracking-[0.12em] text-slate-300">Human-readable reason</p>
                <ul className="mt-2 space-y-1 text-sm text-slate-100">
                  {selectedAlert.humanReasons.map((reason) => (
                    <li key={reason} className="flex items-start gap-2">
                      <span className="mt-1 inline-block h-1.5 w-1.5 rounded-full bg-cyan-300" />
                      <span>{reason}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounded-lg border border-amber-300/35 bg-amber-500/10 p-3 text-sm">
                <p className="text-xs uppercase tracking-[0.12em] text-amber-200">Model confidence interpretation</p>
                <p className="mt-1 text-amber-100">
                  Confidence {Math.round(selectedAlert.modelScores.confidence * 100)}% ({confidenceBand(selectedAlert.modelScores.confidence)}). Alert remains high-risk due to context-weighted risk factors.
                </p>
              </div>

              <div>
                <p className="text-xs uppercase tracking-[0.12em] text-slate-300">Risk factor breakdown</p>
                <div className="mt-2 space-y-2">
                  {selectedAlert.riskFactors.map((factor) => (
                    <div key={factor.factor} className="rounded-lg border border-slate-700/70 bg-slate-900/50 p-2">
                      <div className="flex items-center justify-between text-xs">
                        <span>{factor.factor}</span>
                        <span>{factor.weight}%</span>
                      </div>
                      <p className="mt-1 text-xs text-slate-300">{factor.detail}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </article>

          <article className="panel animate-rise xl:col-span-4">
            <p className="panel-title">Investigation timeline / attack storyline</p>
            <p className="panel-subtitle">Chronological sequence with pivots across user, IP, host, and source.</p>

            <div className="mt-4 space-y-3">
              {selectedAlert.relatedEvents.map((event, index) => (
                <TimelineRow key={`${event.time}-${event.event}`} event={event} index={index} />
              ))}
            </div>

            <div className="mt-5 rounded-lg border border-slate-700/70 bg-slate-900/55 p-3">
              <p className="text-xs uppercase tracking-[0.12em] text-slate-300">Quick pivots</p>
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                <button
                  onClick={() => applyPivot('related')}
                  className="rounded-md border border-cyan-300/40 bg-cyan-400/15 px-2 py-1 text-cyan-100"
                >
                  View related alerts
                </button>
                <button
                  onClick={() => applyPivot('user')}
                  className="rounded-md border border-slate-500/60 bg-slate-800/80 px-2 py-1"
                >
                  Same user activity
                </button>
                <button
                  onClick={() => applyPivot('ip')}
                  className="rounded-md border border-slate-500/60 bg-slate-800/80 px-2 py-1"
                >
                  Same IP activity
                </button>
                <button
                  onClick={() => applyPivot('host')}
                  className="rounded-md border border-slate-500/60 bg-slate-800/80 px-2 py-1"
                >
                  Same host history
                </button>
              </div>
            </div>

            <div className="mt-4 rounded-lg border border-slate-700/70 bg-slate-900/55 p-3">
              <p className="text-xs uppercase tracking-[0.12em] text-slate-300">Search and pivot results</p>
              {searchResults.length ? (
                <div className="mt-2 space-y-2">
                  {searchResults.map((result) => (
                    <button
                      key={`${result.kind}-${result.id}`}
                      className="w-full rounded-lg border border-slate-700/70 bg-slate-950/70 p-2 text-left text-xs transition hover:border-cyan-300/45"
                      onClick={() => {
                        if (result.kind === 'Alert') {
                          setSelectedAlertId(result.id)
                        }
                      }}
                    >
                      <p className="font-semibold text-cyan-100">
                        {result.kind}: {result.title}
                      </p>
                      <p className="mt-1 text-slate-300">{result.subtitle}</p>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="mt-2 text-xs text-slate-400">No search matches yet. Try username, host, IP, hash, process, alert ID, or case ID.</p>
              )}
            </div>

            <div className="mt-4 rounded-lg border border-slate-700/70 bg-slate-900/55 p-3">
              <p className="text-xs uppercase tracking-[0.12em] text-slate-300">Suggested analysis cues</p>
              <div className="mt-2 space-y-2 text-xs">
                {selectedRecommendations.length ? (
                  selectedRecommendations.map((item) => (
                    <div key={item.id} className="rounded-lg border border-slate-700/70 bg-slate-950/70 p-2">
                      <p className="font-semibold text-cyan-100">{item.riskIfNoAction}</p>
                      <p className="text-slate-300">{item.rationale}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-slate-400">No additional analysis cues were generated.</p>
                )}
              </div>
            </div>
          </article>
        </section>
      ) : null}
    </>
  )
}
