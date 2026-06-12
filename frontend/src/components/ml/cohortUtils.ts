// frontend/src/components/ml/cohortUtils.ts

export type Period = 'day' | 'week' | 'month' | 'quarter' | 'year'

export const PANEL_COLORS = [
  { dot: '#3b82f6', rgba: '59,130,246',  text: 'text-blue-400',   border: 'rgba(59,130,246,0.25)',  header: '#0f1929', badge: 'rgba(59,130,246,0.1)',  badgeBorder: 'rgba(59,130,246,0.2)',  badgeText: '#93c5fd' },
  { dot: '#a855f7', rgba: '168,85,247',  text: 'text-purple-400', border: 'rgba(168,85,247,0.25)', header: '#150f29', badge: 'rgba(168,85,247,0.1)', badgeBorder: 'rgba(168,85,247,0.2)', badgeText: '#d8b4fe' },
  { dot: '#22c55e', rgba: '34,197,94',   text: 'text-green-400',  border: 'rgba(34,197,94,0.25)',  header: '#0f1f12', badge: 'rgba(34,197,94,0.1)',  badgeBorder: 'rgba(34,197,94,0.2)',  badgeText: '#86efac'  },
] as const

export function cellBg(pct: number | null, rgba: string): string {
  if (pct === null) return 'transparent'
  if (pct === 0) return `rgba(${rgba},0.06)`
  const alpha = Math.min(1, 0.12 + (pct / 100) * 0.88)
  return `rgba(${rgba},${alpha.toFixed(2)})`
}

export function cellText(pct: number | null): string {
  if (pct === null) return ''
  if (pct >= 35) return 'text-white'
  if (pct >= 15) return 'text-blue-200'
  return 'text-blue-400'
}
