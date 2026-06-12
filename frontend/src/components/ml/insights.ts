import { fmtFull } from './numFormat'

/**
 * Build 1–2 Vietnamese insight sentences from a labelled numeric series:
 * highest/lowest point, overall trend (first↔last), and anomaly count (|z|>2).
 * Pure & deterministic.
 *
 * Example: describeSeries(["T1","T2","T3","T4"], [10, 12, 9, 30])
 *   → "Cao nhất tại T4 (30); thấp nhất tại T3 (9). Xu hướng tăng (+200% từ đầu kỳ). 1 điểm bất thường (|z|>2)."
 */
export function describeSeries(labels: string[], values: (number | null)[]): string {
  const pts = labels
    .map((label, i) => ({ label, v: values[i] }))
    .filter((p): p is { label: string; v: number } => typeof p.v === 'number' && !Number.isNaN(p.v))
  if (pts.length < 2) return ''

  let hi = pts[0], lo = pts[0]
  for (const p of pts) { if (p.v > hi.v) hi = p; if (p.v < lo.v) lo = p }

  const first = pts[0].v, last = pts[pts.length - 1].v
  const sentences: string[] = []
  sentences.push(`Cao nhất tại ${hi.label} (${fmtFull(hi.v)}); thấp nhất tại ${lo.label} (${fmtFull(lo.v)}).`)
  sentences.push(formatTrend(first, last))

  const mean = pts.reduce((s, p) => s + p.v, 0) / pts.length
  const variance = pts.reduce((s, p) => s + (p.v - mean) ** 2, 0) / pts.length
  const std = Math.sqrt(variance)
  const anomalies = std > 0 ? pts.filter(p => Math.abs((p.v - mean) / std) > 2).length : 0
  if (anomalies > 0) sentences.push(`${anomalies} điểm bất thường (|z|>2).`)

  return sentences.filter(Boolean).join(' ')
}

export function formatTrend(first: number, last: number): string {
  if (first === 0) {
    if (last === 0) return 'Xu hướng đi ngang.'
    return last > 0 ? 'Xu hướng tăng từ 0.' : 'Xu hướng giảm xuống âm.'
  }
  const pct = ((last - first) / Math.abs(first)) * 100
  const dir = pct > 1 ? 'tăng' : pct < -1 ? 'giảm' : 'đi ngang'
  if (dir === 'đi ngang') return 'Xu hướng đi ngang.'
  const sign = pct > 0 ? '+' : ''
  return `Xu hướng ${dir} (${sign}${pct.toFixed(0)}% từ đầu kỳ).`
}
