import ReactECharts from 'echarts-for-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  alerts,
  alertsBySeverity,
  alertsBySource,
  analyticsMetrics,
  mitreCoverage,
  trend24h,
  trend7d,
} from '../data/mockData'
import { exportReportingCsv, exportReportingPdf } from '../utils/exporters'

const piePalette = ['#22d3ee', '#1d4ed8', '#38bdf8', '#f59e0b', '#10b981']

export function ReportingPage() {
  const heatmapOption = buildMitreHeatmapOption()

  const handleExportCsv = () => {
    exportReportingCsv({
      analyticsMetrics,
      trend24h,
      trend7d,
      alerts,
      mitreCoverage,
    })
  }

  const handleExportPdf = () => {
    exportReportingPdf({
      analyticsMetrics,
      trend24h,
      trend7d,
      alerts,
      mitreCoverage,
    })
  }

  return (
    <>
      <section className="panel animate-rise">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="panel-title">Analytics / reporting workspace</p>
            <p className="panel-subtitle">Executive SOC reporting with export-ready charting and attack coverage intelligence.</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleExportCsv}
              className="rounded-lg border border-cyan-300/40 bg-cyan-400/15 px-3 py-2 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-400/30"
            >
              Export CSV
            </button>
            <button
              onClick={handleExportPdf}
              className="rounded-lg border border-amber-300/40 bg-amber-400/15 px-3 py-2 text-sm font-semibold text-amber-100 transition hover:bg-amber-400/30"
            >
              Export PDF
            </button>
          </div>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {analyticsMetrics.map((metric) => (
            <div key={metric.label} className="rounded-xl border border-slate-700/75 bg-slate-900/55 p-3">
              <p className="text-xs uppercase tracking-[0.1em] text-slate-300">{metric.label}</p>
              <p className="mt-1 text-2xl font-semibold text-slate-100">{metric.value}</p>
              <p className="text-xs text-cyan-200">{metric.trend}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-12">
        <article className="panel animate-rise xl:col-span-7">
          <p className="panel-title">24h alerts trend (Recharts)</p>
          <p className="panel-subtitle">Operational surge visibility for rapid SOC briefing.</p>
          <div className="mt-3 h-72 rounded-xl border border-slate-800/80 bg-slate-950/40 p-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trend24h}>
                <defs>
                  <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#22d3ee" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f3557" />
                <XAxis dataKey="label" stroke="#9db6dd" tick={{ fontSize: 12 }} />
                <YAxis stroke="#9db6dd" tick={{ fontSize: 12 }} />
                <Tooltip
                  contentStyle={{ background: '#08122a', border: '1px solid #1f3557', color: '#dce7ff' }}
                  cursor={{ fill: 'rgba(34, 211, 238, 0.12)' }}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#22d3ee"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#trendGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel animate-rise xl:col-span-5">
          <p className="panel-title">Alert source composition (Recharts)</p>
          <p className="panel-subtitle">Source performance and telemetry contribution balance.</p>
          <div className="mt-3 h-72 rounded-xl border border-slate-800/80 bg-slate-950/40 p-2">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={alertsBySource}
                  dataKey="value"
                  nameKey="label"
                  cx="50%"
                  cy="50%"
                  outerRadius={98}
                  innerRadius={52}
                  paddingAngle={2}
                >
                  {alertsBySource.map((entry, index) => (
                    <Cell key={entry.label} fill={piePalette[index % piePalette.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#08122a', border: '1px solid #1f3557', color: '#dce7ff' }}
                />
                <Legend wrapperStyle={{ color: '#dce7ff', fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </article>
      </section>

      <section className="grid gap-4 xl:grid-cols-12">
        <article className="panel animate-rise xl:col-span-6">
          <p className="panel-title">Severity distribution (Recharts)</p>
          <p className="panel-subtitle">High/Critical concentration and queue pressure.</p>
          <div className="mt-3 h-72 rounded-xl border border-slate-800/80 bg-slate-950/40 p-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={alertsBySeverity}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f3557" />
                <XAxis dataKey="label" stroke="#9db6dd" tick={{ fontSize: 12 }} />
                <YAxis stroke="#9db6dd" tick={{ fontSize: 12 }} />
                <Tooltip
                  contentStyle={{ background: '#08122a', border: '1px solid #1f3557', color: '#dce7ff' }}
                />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {alertsBySeverity.map((entry, index) => (
                    <Cell
                      key={entry.label}
                      fill={['#ef4444', '#f97316', '#f59e0b', '#22c55e'][index] ?? '#38bdf8'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel animate-rise xl:col-span-6">
          <p className="panel-title">MITRE coverage matrix (ECharts)</p>
          <p className="panel-subtitle">Technique intensity by tactic for maturity and gap communication.</p>
          <div className="mt-3 h-72 rounded-xl border border-slate-800/80 bg-slate-950/40 p-2">
            <ReactECharts option={heatmapOption} style={{ height: '100%', width: '100%' }} notMerge lazyUpdate />
          </div>
        </article>
      </section>

      <section className="panel animate-rise">
        <p className="panel-title">Weekly trend and risk summary</p>
        <p className="panel-subtitle">Leadership-ready trendline from 7-day operational telemetry.</p>

        <div className="mt-3 h-72 rounded-xl border border-slate-800/80 bg-slate-950/40 p-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={trend7d}>
              <defs>
                <linearGradient id="weekGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#60a5fa" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f3557" />
              <XAxis dataKey="label" stroke="#9db6dd" tick={{ fontSize: 12 }} />
              <YAxis stroke="#9db6dd" tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{ background: '#08122a', border: '1px solid #1f3557', color: '#dce7ff' }}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#60a5fa"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#weekGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </section>
    </>
  )
}

function buildMitreHeatmapOption() {
  const tactics = Array.from(new Set(mitreCoverage.map((item) => item.tactic)))
  const techniques = mitreCoverage.map((item) => item.techniqueId)

  const data = mitreCoverage.map((item, index) => {
    const x = index
    const y = tactics.indexOf(item.tactic)
    return [x, y, item.alerts]
  })

  return {
    backgroundColor: 'transparent',
    tooltip: {
      position: 'top',
      backgroundColor: '#08122a',
      borderColor: '#1f3557',
      textStyle: { color: '#dce7ff' },
      formatter: (params: { value: [number, number, number] }) => {
        const [x, y, count] = params.value
        return `${techniques[x]}<br/>${tactics[y]}<br/>Alerts: ${count}`
      },
    },
    grid: { left: 60, right: 20, top: 40, bottom: 55 },
    xAxis: {
      type: 'category',
      data: techniques,
      axisLabel: { color: '#a9bfdc', fontSize: 11, rotate: 20 },
      axisLine: { lineStyle: { color: '#274166' } },
    },
    yAxis: {
      type: 'category',
      data: tactics,
      axisLabel: { color: '#a9bfdc', fontSize: 11 },
      axisLine: { lineStyle: { color: '#274166' } },
    },
    visualMap: {
      min: 0,
      max: 25,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 8,
      textStyle: { color: '#c7d9f4' },
      inRange: { color: ['#0f172a', '#1d4ed8', '#22d3ee', '#f59e0b'] },
    },
    series: [
      {
        type: 'heatmap',
        data,
        label: {
          show: true,
          color: '#e2edff',
          fontSize: 10,
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 12,
            shadowColor: 'rgba(34,211,238,0.55)',
          },
        },
      },
    ],
  }
}
