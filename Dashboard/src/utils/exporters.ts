import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'
import type {
  AlertRecord,
  AnalyticsMetric,
  MitreCoverageRecord,
  TrendPoint,
} from '../types'

interface ReportingExportPayload {
  analyticsMetrics: AnalyticsMetric[]
  trend24h: TrendPoint[]
  trend7d: TrendPoint[]
  alerts: AlertRecord[]
  mitreCoverage: MitreCoverageRecord[]
}

export function exportReportingCsv(payload: ReportingExportPayload) {
  const lines: string[] = []

  lines.push('SecureBot SOC Report')
  lines.push(`Generated At,${new Date().toISOString()}`)
  lines.push('')

  lines.push('Analytics Metrics')
  lines.push(csvRow(['Metric', 'Value', 'Trend']))
  payload.analyticsMetrics.forEach((item) => {
    lines.push(csvRow([item.label, item.value, item.trend]))
  })
  lines.push('')

  lines.push('Alert Trend 24h')
  lines.push(csvRow(['Time', 'Alerts']))
  payload.trend24h.forEach((point) => {
    lines.push(csvRow([point.label, String(point.value)]))
  })
  lines.push('')

  lines.push('Alert Trend 7d')
  lines.push(csvRow(['Day', 'Alerts']))
  payload.trend7d.forEach((point) => {
    lines.push(csvRow([point.label, String(point.value)]))
  })
  lines.push('')

  lines.push('Top Alerts')
  lines.push(
    csvRow([
      'Alert ID',
      'Timestamp',
      'Host',
      'User',
      'Detection Label',
      'Anomaly Score',
      'Risk Score',
      'Severity',
      'Technique',
      'Status',
      'Source',
    ]),
  )
  payload.alerts.slice(0, 30).forEach((alert) => {
    lines.push(
      csvRow([
        alert.id,
        alert.timestamp,
        alert.host,
        alert.user,
        alert.detectionLabel,
        alert.modelScores.combined.toFixed(2),
        alert.riskScore.toFixed(2),
        alert.severity,
        alert.mitreTechnique,
        alert.status,
        alert.source,
      ]),
    )
  })
  lines.push('')

  lines.push('MITRE Coverage')
  lines.push(csvRow(['Technique ID', 'Technique', 'Tactic', 'Alerts']))
  payload.mitreCoverage.forEach((row) => {
    lines.push(csvRow([row.techniqueId, row.technique, row.tactic, String(row.alerts)]))
  })

  downloadFile('securebot-soc-report.csv', lines.join('\n'), 'text/csv;charset=utf-8;')
}

export function exportReportingPdf(payload: ReportingExportPayload) {
  const doc = new jsPDF({ unit: 'mm', format: 'a4' })

  doc.setFillColor(7, 24, 52)
  doc.rect(0, 0, 210, 24, 'F')
  doc.setTextColor(226, 242, 255)
  doc.setFontSize(14)
  doc.text('SecureBot SOC Reporting Snapshot', 14, 14)

  doc.setTextColor(70, 70, 70)
  doc.setFontSize(9)
  doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 30)

  autoTable(doc, {
    startY: 34,
    head: [['Metric', 'Value', 'Trend']],
    body: payload.analyticsMetrics.map((item) => [item.label, item.value, item.trend]),
    styles: { fontSize: 8 },
    headStyles: { fillColor: [12, 52, 96] },
  })
  const metricsFinalY =
    ((doc as jsPDF & { lastAutoTable?: { finalY: number } }).lastAutoTable?.finalY ?? 34) + 6

  autoTable(doc, {
    startY: metricsFinalY,
    head: [['Alert', 'Host', 'User', 'Risk', 'Severity', 'Technique']],
    body: payload.alerts.slice(0, 12).map((alert) => [
      alert.id,
      alert.host,
      alert.user,
      alert.riskScore.toFixed(2),
      alert.severity,
      alert.mitreTechnique,
    ]),
    styles: { fontSize: 8 },
    headStyles: { fillColor: [17, 95, 140] },
  })
  const alertsFinalY =
    ((doc as jsPDF & { lastAutoTable?: { finalY: number } }).lastAutoTable?.finalY ?? metricsFinalY) +
    6

  autoTable(doc, {
    startY: alertsFinalY,
    head: [['Technique', 'Tactic', 'Alerts']],
    body: payload.mitreCoverage.map((row) => [row.techniqueId, row.tactic, String(row.alerts)]),
    styles: { fontSize: 8 },
    headStyles: { fillColor: [16, 124, 102] },
  })

  doc.save('securebot-soc-report.pdf')
}

function csvRow(values: string[]) {
  return values
    .map((value) => {
      const escaped = value.replaceAll('"', '""')
      return `"${escaped}"`
    })
    .join(',')
}

function downloadFile(fileName: string, content: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = fileName
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
