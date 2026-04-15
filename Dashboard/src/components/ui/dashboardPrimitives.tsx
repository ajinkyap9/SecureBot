import type { AlertStatus, ApprovalRecord, Severity, TimelineEvent } from '../../types'

export function MetricCard({
  label,
  value,
  hint,
  tone,
}: {
  label: string
  value: string
  hint: string
  tone: 'sky' | 'indigo' | 'teal' | 'red' | 'emerald' | 'amber'
}) {
  const toneClass: Record<typeof tone, string> = {
    sky: 'from-sky-300/30 to-blue-500/20 border-sky-300/30',
    indigo: 'from-indigo-300/30 to-blue-600/20 border-indigo-300/30',
    teal: 'from-teal-300/30 to-cyan-500/20 border-teal-300/30',
    red: 'from-red-300/30 to-orange-500/20 border-red-300/30',
    emerald: 'from-emerald-300/30 to-lime-500/20 border-emerald-300/30',
    amber: 'from-amber-300/30 to-orange-500/20 border-amber-300/30',
  }

  return (
    <article className={`panel animate-rise border bg-gradient-to-b ${toneClass[tone]}`}>
      <p className="panel-title">{label}</p>
      <p className="stat-value">{value}</p>
      <p className="panel-subtitle">{hint}</p>
    </article>
  )
}

export function BarItem({
  label,
  value,
  maxValue,
  mode,
}: {
  label: string
  value: number
  maxValue: number
  mode: 'severity' | 'source'
}) {
  const width = Math.max(8, (value / maxValue) * 100)
  const color =
    mode === 'severity'
      ? 'bg-gradient-to-r from-cyan-300 to-blue-500'
      : 'bg-gradient-to-r from-emerald-300 to-teal-500'

  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-slate-200">{label}</span>
        <span className="font-mono text-slate-100">{value}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-800">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${width}%` }} />
      </div>
    </div>
  )
}

export function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: string[]
  onChange: (value: string) => void
}) {
  return (
    <label className="rounded-xl border border-slate-700/70 bg-slate-900/55 px-2 py-1.5">
      <p className="text-[10px] uppercase tracking-[0.12em] text-slate-400">{label}</p>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full bg-transparent text-xs outline-none"
      >
        {options.map((option) => (
          <option key={option} value={option} className="bg-slate-900">
            {option}
          </option>
        ))}
      </select>
    </label>
  )
}

export function ScoreCard({ title, value }: { title: string; value: number }) {
  return (
    <div className="rounded-lg border border-slate-700/70 bg-slate-950/50 p-2.5">
      <p className="text-xs uppercase tracking-[0.12em] text-slate-400">{title}</p>
      <p className="mt-1 font-mono text-xl text-cyan-100">{value.toFixed(2)}</p>
    </div>
  )
}

export function TimelineRow({ event, index }: { event: TimelineEvent; index: number }) {
  return (
    <div className="relative rounded-xl border border-slate-700/70 bg-slate-900/55 p-3">
      <div className="absolute -left-1.5 top-5 h-3 w-3 rounded-full bg-cyan-300" />
      {index < 4 ? <div className="absolute -left-[1px] top-8 h-10 w-[1px] bg-cyan-300/50" /> : null}
      <div className="ml-3">
        <p className="font-mono text-xs text-cyan-100">{event.time}</p>
        <p className="mt-1 text-sm text-slate-100">{event.event}</p>
        <p className="mt-1 text-xs text-slate-300">
          {event.source} | {event.user} | {event.host} | {event.ip}
        </p>
        <span className="mt-1 inline-block rounded-full border border-slate-600/70 px-2 py-0.5 text-[10px] uppercase tracking-[0.1em] text-slate-300">
          Pivot: {event.pivot}
        </span>
      </div>
    </div>
  )
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const classMap: Record<Severity, string> = {
    Critical: 'bg-red-500/20 text-red-100 border-red-300/35',
    High: 'bg-orange-500/20 text-orange-100 border-orange-300/35',
    Medium: 'bg-amber-500/20 text-amber-100 border-amber-300/35',
    Low: 'bg-emerald-500/20 text-emerald-100 border-emerald-300/35',
  }

  return <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${classMap[severity]}`}>{severity}</span>
}

export function StatusBadge({ status }: { status: AlertStatus }) {
  const classMap: Record<AlertStatus, string> = {
    New: 'bg-slate-500/20 text-slate-100 border-slate-300/30',
    'Under Review': 'bg-cyan-500/20 text-cyan-100 border-cyan-300/35',
    Escalated: 'bg-red-500/20 text-red-100 border-red-300/35',
    Resolved: 'bg-emerald-500/20 text-emerald-100 border-emerald-300/35',
  }

  return <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${classMap[status]}`}>{status}</span>
}

export function StatusTag({ status }: { status: ApprovalRecord['status'] }) {
  const classMap: Record<ApprovalRecord['status'], string> = {
    Pending: 'bg-slate-500/20 text-slate-100 border-slate-300/30',
    Approved: 'bg-emerald-500/20 text-emerald-100 border-emerald-300/35',
    Rejected: 'bg-red-500/20 text-red-100 border-red-300/35',
  }

  return <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${classMap[status]}`}>{status}</span>
}

export function ResultTag({ result }: { result: 'Success' | 'Failed' | 'Pending' }) {
  const classMap: Record<'Success' | 'Failed' | 'Pending', string> = {
    Success: 'bg-emerald-500/20 text-emerald-100 border-emerald-300/35',
    Failed: 'bg-red-500/20 text-red-100 border-red-300/35',
    Pending: 'bg-amber-500/20 text-amber-100 border-amber-300/35',
  }

  return <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${classMap[result]}`}>{result}</span>
}

export function HealthTag({ status }: { status: 'Healthy' | 'Warning' | 'Critical' }) {
  const classMap: Record<'Healthy' | 'Warning' | 'Critical', string> = {
    Healthy: 'bg-emerald-500/20 text-emerald-100 border-emerald-300/35',
    Warning: 'bg-amber-500/20 text-amber-100 border-amber-300/35',
    Critical: 'bg-red-500/20 text-red-100 border-red-300/35',
  }

  return <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${classMap[status]}`}>{status}</span>
}

export function InfoTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-700/70 bg-slate-950/40 p-2">
      <p className="text-[10px] uppercase tracking-[0.08em] text-slate-400">{label}</p>
      <p className="mt-1 text-xs text-slate-100">{value}</p>
    </div>
  )
}
