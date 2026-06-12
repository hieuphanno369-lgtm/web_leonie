// frontend/src/components/ml/numFormat.ts
// Định dạng số trục Y dùng chung cho mọi biểu đồ ML Studio.
export type YScale = 'auto' | 'K' | 'M' | 'B' | '%'

export function autoScale(maxAbs: number): YScale {
  if (maxAbs >= 1e9) return 'B'
  if (maxAbs >= 1e6) return 'M'
  if (maxAbs >= 1e3) return 'K'
  return 'auto'
}

export function fmtY(v: number, scale: YScale, maxAbs: number): string {
  const s = scale === 'auto' ? autoScale(maxAbs) : scale
  if (scale === '%') return `${v.toFixed(1)}%`
  if (s === 'B') return `${(v / 1e9).toFixed(2)}B`
  if (s === 'M') return `${(v / 1e6).toFixed(2)}M`
  if (s === 'K') return `${(v / 1e3).toFixed(1)}K`
  return v.toLocaleString('vi-VN', { maximumFractionDigits: 2 })
}

export function fmtFull(v: number): string {
  return v.toLocaleString('vi-VN', { maximumFractionDigits: 2 })
}
