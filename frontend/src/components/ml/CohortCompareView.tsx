// frontend/src/components/ml/CohortCompareView.tsx
import { useState, useEffect } from 'react'
import { Users, Plus, X } from 'lucide-react'
import type { DatasetInfo, QualityResult } from '../../types'
import { runCohort, fetchColumnValues, type CohortResult } from '../../api/ml'
import { type Period, PANEL_COLORS, cellBg } from './cohortUtils'
import DataQualityBanner from './DataQualityBanner'
import { MSG } from '../../messages'

interface PanelConfig {
  id: string
  dataset_id: string
  filter_col: string
  filter_val: string
  filterOpts: string[]
}

type PanelResult = CohortResult | { error: string } | null

interface Props {
  dataset: DatasetInfo
  datasets: DatasetInfo[]
  quality: QualityResult | null
  qualityError?: boolean
}

function makePanel(dataset_id: string): PanelConfig {
  return { id: crypto.randomUUID(), dataset_id, filter_col: '', filter_val: '', filterOpts: [] }
}

interface PanelCardProps {
  idx: number
  panel: PanelConfig
  datasets: DatasetInfo[]
  colorIdx: number
  result: PanelResult
  loading: boolean
  canRemove: boolean
  dateCol: string
  userCol: string
  period: Period
  onUpdate: (patch: Partial<PanelConfig>) => void
  onRemove: () => void
}

function periodLabel(n: number, period: Period): string {
  if (period === 'day')     return `D${n}`
  if (period === 'week')    return `Wk${n}`
  if (period === 'quarter') return `Q${n}`
  if (period === 'year')    return `Yr${n}`
  return `Mo${n}`
}

function avgRetention(result: CohortResult): (number | null)[] {
  return result.periods.map((_, pi) => {
    const vals = result.matrix
      .map(row => row[pi])
      .filter((v): v is number => v !== null)
    return vals.length > 0 ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length) : null
  })
}

function PanelCard({ idx, panel, datasets, colorIdx, result, loading, period, canRemove, onUpdate, onRemove }: PanelCardProps) {
  const color = PANEL_COLORS[colorIdx % PANEL_COLORS.length]

  useEffect(() => {
    if (!panel.filter_col) {
      onUpdate({ filterOpts: [], filter_val: '' })
      return
    }
    const controller = new AbortController()
    fetchColumnValues(panel.dataset_id, panel.filter_col, controller.signal)
      .then(vals => onUpdate({ filterOpts: vals, filter_val: vals[0] ?? '' }))
      .catch(err => {
        // Ignore cancellation errors (component unmounted or deps changed)
        if ((err as { name?: string })?.name !== 'CanceledError') {
          onUpdate({ filterOpts: [], filter_val: '' })
        }
      })
    return () => controller.abort()
    // onUpdate intentionally omitted — it's a new arrow fn each render and
    // would cause an infinite loop; only data-driving deps are needed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [panel.filter_col, panel.dataset_id])

  return (
    <div style={{ border: `1px solid ${color.border}`, borderRadius: 6, overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ background: color.header, borderBottom: `1px solid ${color.border}` }}
           className="flex items-center gap-2 px-3 py-2">
        <div style={{ background: color.dot, width: 8, height: 8, borderRadius: '50%' }} />
        <span style={{ color: color.dot }} className="text-[11px] font-semibold">
          Panel {String.fromCharCode(65 + idx)}
        </span>
        <button onClick={onRemove} disabled={!canRemove} aria-label="Remove panel"
          className="ml-auto text-gray-600 hover:text-gray-400 disabled:opacity-20 transition-colors">
          <X size={12} />
        </button>
      </div>

      {/* Config row */}
      <div className="flex flex-wrap gap-2 px-3 py-2 border-b border-white/5">
        <div>
          <label className="block text-[10px] text-gray-500 mb-1">Dataset</label>
          <select className="input-base text-xs" value={panel.dataset_id}
            onChange={e => onUpdate({ dataset_id: e.target.value, filter_col: '', filter_val: '', filterOpts: [] })}>
            {datasets.map(d => <option key={d.file_id} value={d.file_id}>{d.filename}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-[10px] text-gray-500 mb-1">Filter col</label>
          <select className="input-base text-xs" value={panel.filter_col}
            onChange={e => onUpdate({ filter_col: e.target.value, filter_val: '', filterOpts: [] })}>
            <option value="">— none —</option>
            {(datasets.find(d => d.file_id === panel.dataset_id)?.columns ?? [])
              .map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
          </select>
        </div>
        {panel.filter_col && panel.filterOpts.length > 0 && (
          <div>
            <label className="block text-[10px] text-gray-500 mb-1">Value</label>
            <select className="input-base text-xs" value={panel.filter_val}
              onChange={e => onUpdate({ filter_val: e.target.value })}>
              {panel.filterOpts.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
        )}
      </div>

      {/* Result area */}
      <div className="overflow-auto" style={{ maxHeight: 400 }}>
        {'error' in (result ?? {}) ? (
          <div className="px-3 py-3">
            <p className="text-danger text-xs">{(result as { error: string }).error}</p>
          </div>
        ) : result && (result as CohortResult).suitable === false ? (
          <div className="px-3 py-3">
            <p className="text-amber-400 text-xs font-semibold mb-1">Không phù hợp cohort</p>
            <ul className="list-disc pl-4 text-gray-500 text-[10px] space-y-0.5">
              {(result as CohortResult).reasons?.map((r, i) => <li key={i}>{r}</li>)}
            </ul>
          </div>
        ) : result ? (
          <>
            <table className="text-[10px] border-collapse w-full">
              <thead>
                <tr className="bg-[#0d1117]">
                  <th className="sticky left-0 z-10 bg-[#0d1117] px-2 py-1.5 text-left text-gray-400 font-medium whitespace-nowrap border-b border-white/5">
                    Cohort
                  </th>
                  <th className="px-2 py-1.5 text-right text-gray-400 font-medium border-b border-white/5">N</th>
                  {(result as CohortResult).periods.map(n => (
                    <th key={n} className="px-1.5 py-1.5 text-center text-gray-500 font-medium whitespace-nowrap border-b border-white/5 min-w-[40px]">
                      {periodLabel(n, period)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(result as CohortResult).cohorts.map((label, ri) => (
                  <tr key={label} className="border-b border-white/5 hover:bg-white/[0.02]">
                    <td className="sticky left-0 z-10 bg-[#0d1117] px-2 py-1 text-gray-300 font-medium whitespace-nowrap">
                      {label}
                    </td>
                    <td className="px-2 py-1 text-right text-gray-500 whitespace-nowrap">
                      {(result as CohortResult).cohort_sizes[ri].toLocaleString()}
                    </td>
                    {(result as CohortResult).matrix[ri].map((pct, ci) => (
                      <td key={ci}
                        title={pct !== null ? `${pct}%` : undefined}
                        // Inline colour (not cellText) — panel-aware hue per colour theme
                        style={{ background: cellBg(pct, color.rgba), color: pct !== null ? (pct >= 35 ? '#fff' : pct >= 15 ? color.badgeText : color.dot) : undefined }}
                        className="px-1.5 py-1 text-center font-medium"
                      >
                        {pct !== null ? `${pct}%` : ''}
                      </td>
                    ))}
                  </tr>
                ))}
                {(result as CohortResult).all_users_row && (
                  <tr className="border-t-2 border-white/10 bg-white/[0.03]">
                    <td className="sticky left-0 z-10 bg-[#161b22] px-2 py-1.5 text-white font-semibold whitespace-nowrap">All</td>
                    <td className="px-2 py-1.5 text-right text-gray-300 font-semibold">
                      {((result as CohortResult).all_users_size ?? 0).toLocaleString()}
                    </td>
                    {(result as CohortResult).all_users_row!.map((pct, ci) => (
                      <td key={ci}
                        title={pct !== null ? `${pct}%` : undefined}
                        style={{ background: cellBg(pct, color.rgba), color: pct !== null ? (pct >= 35 ? '#fff' : pct >= 15 ? color.badgeText : color.dot) : undefined }}
                        className="px-1.5 py-1.5 text-center font-semibold"
                      >
                        {pct !== null ? `${pct}%` : ''}
                      </td>
                    ))}
                  </tr>
                )}
              </tbody>
            </table>
            {/* Colour legend */}
            <div className="flex items-center gap-2 px-3 py-1.5 border-t border-white/5">
              <span className="text-[9px] text-gray-600">Retention %</span>
              <div className="flex gap-0.5">
                {[0, 20, 40, 60, 80, 100].map(v => (
                  <div key={v} style={{ background: cellBg(v, color.rgba), width: 14, height: 8, borderRadius: 2 }} />
                ))}
              </div>
              <span className="text-[9px] text-gray-600">0→100%</span>
            </div>
            {/* Avg retention sparkline */}
            {(() => {
              const avgs = avgRetention(result as CohortResult)
              const periods = (result as CohortResult).periods
              if (avgs.length < 2) return null
              const w = 200, h = 28, pad = 8
              const maxV = 100
              const xStep = (w - pad * 2) / Math.max(avgs.length - 1, 1)
              const points = avgs
                .map((v, i) => v !== null ? `${pad + i * xStep},${h - pad - ((v / maxV) * (h - pad * 2))}` : null)
                .filter((p): p is string => p !== null)
                .join(' ')
              return (
                <div className="px-3 pb-2 border-t border-white/5">
                  <div className="text-[9px] text-gray-600 mb-1">Avg retention</div>
                  <svg viewBox={`0 0 ${w} ${h}`} style={{ width: '100%', height: h }}>
                    <polyline points={points} fill="none" stroke={color.dot} strokeWidth="1.5" />
                    {avgs.map((v, i) => v !== null ? (
                      <circle key={i} cx={pad + i * xStep} cy={h - pad - (v / maxV) * (h - pad * 2)}
                        r="2" fill={color.dot} />
                    ) : null)}
                    <text x={pad} y={h} fill="#6b7280" fontSize="6">{periodLabel(periods[0], period)}</text>
                    <text x={w - pad} y={h} fill="#6b7280" fontSize="6" textAnchor="end">
                      {periodLabel(periods[periods.length - 1], period)}
                    </text>
                  </svg>
                </div>
              )
            })()}
          </>
        ) : loading ? (
          <div className="flex items-center justify-center py-6">
            <span className="w-4 h-4 border-2 border-gray-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="flex items-center justify-center py-6 text-gray-700 text-xs">
            {MSG.cohortRunAllHint}
          </div>
        )}
      </div>
    </div>
  )
}

export default function CohortCompareView({ dataset, datasets, quality, qualityError }: Props) {
  const cols = dataset.columns.map(c => c.name)
  const defaultDate = cols.find(c => /date|time|day|month|period|cohort/i.test(c)) ?? cols[0] ?? ''
  const defaultUser = cols.find(c => c !== defaultDate && /id|user|cust|key/i.test(c))
    ?? cols.find(c => c !== defaultDate) ?? cols[0] ?? ''

  const [dateCol,  setDateCol]  = useState(defaultDate)
  const [userCol,  setUserCol]  = useState(defaultUser)
  const [period,   setPeriod]   = useState<Period>('month')
  const [panels,   setPanels]   = useState<PanelConfig[]>(() => [
    makePanel(dataset.file_id),
    makePanel(dataset.file_id),
  ])
  const [results,  setResults]  = useState<PanelResult[]>([null, null])
  const [loading,  setLoading]  = useState(false)

  function addPanel() {
    if (panels.length >= 3) return
    setPanels(prev => [...prev, makePanel(dataset.file_id)])
    setResults(prev => [...prev, null])
  }

  function removePanel(idx: number) {
    if (panels.length <= 1) return
    setPanels(prev => prev.filter((_, i) => i !== idx))
    setResults(prev => prev.filter((_, i) => i !== idx))
  }

  function updatePanel(idx: number, patch: Partial<PanelConfig>) {
    setPanels(prev => prev.map((p, i) => i === idx ? { ...p, ...patch } : p))
  }

  useEffect(() => {
    const newDate = dataset.columns.find(c => /date|time|day|month|period|cohort/i.test(c.name))?.name ?? dataset.columns[0]?.name ?? ''
    const newUser = dataset.columns.find(c => /id|user|cust|key/i.test(c.name) && c.name !== newDate)?.name ?? dataset.columns.find(c => c.name !== newDate)?.name ?? dataset.columns[0]?.name ?? ''
    setDateCol(newDate)
    setUserCol(newUser)
    setPanels([makePanel(dataset.file_id), makePanel(dataset.file_id)])
    setResults([null, null])
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataset.file_id])

  async function handleRunAll() {
    setLoading(true)
    setResults(panels.map(() => null))
    const settled = await Promise.allSettled(
      panels.map(p =>
        runCohort(
          p.dataset_id, dateCol, userCol, period,
          p.filter_col || undefined, p.filter_val || undefined,
        )
      )
    )
    setResults(
      settled.map(r =>
        r.status === 'fulfilled'
          ? r.value
          : { error: (r.reason as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? MSG.cohortFailed }
      )
    )
    setLoading(false)
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <DataQualityBanner quality={quality} qualityError={qualityError} />

      {/* Shared config bar */}
      <div className="flex flex-wrap gap-3 items-end px-4 py-3 border-b border-white/5 flex-shrink-0 bg-[#161b22]/40">
        <span className="text-[10px] text-gray-600 self-center">Shared:</span>

        <div>
          <label className="block text-[10px] text-gray-500 mb-1">Cohort col</label>
          <select className="input-base text-xs" value={dateCol} onChange={e => setDateCol(e.target.value)}>
            {cols.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        <div>
          <label className="block text-[10px] text-gray-500 mb-1">ID / Count col</label>
          <select className="input-base text-xs" value={userCol} onChange={e => setUserCol(e.target.value)}>
            {cols.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        <div>
          <label className="block text-[10px] text-gray-500 mb-1">Period</label>
          <div className="flex gap-1">
            {(['day', 'week', 'month', 'quarter', 'year'] as Period[]).map(p => (
              <button key={p} onClick={() => setPeriod(p)}
                className={`px-2 py-1 rounded text-[11px] border transition-all capitalize ${
                  period === p
                    ? 'bg-data/10 text-data border-data/30'
                    : 'text-gray-500 border-transparent hover:text-gray-300'
                }`}>{p}</button>
            ))}
          </div>
        </div>

        <div className="flex gap-2 ml-auto items-center">
          <button
            onClick={addPanel}
            disabled={panels.length >= 3}
            className="flex items-center gap-1 px-2 py-1.5 text-[11px] border border-white/10 rounded text-gray-400 hover:text-gray-200 disabled:opacity-30 transition-all"
          >
            <Plus size={11} /> Panel
          </button>
          <button
            onClick={handleRunAll}
            disabled={loading || !dateCol || !userCol}
            className="px-3 py-1.5 bg-data/10 hover:bg-data/20 text-data border border-data/20 rounded text-xs font-medium transition-all disabled:opacity-40 flex items-center gap-1.5"
          >
            {loading
              ? <><span className="w-3 h-3 border border-data border-t-transparent rounded-full animate-spin" /> Running…</>
              : <><Users size={12} /> Run All</>}
          </button>
        </div>
      </div>

      {/* Panel grid */}
      <div className={`flex-1 overflow-auto p-3 grid gap-3 ${panels.length === 3 ? 'grid-cols-3' : panels.length === 2 ? 'grid-cols-2' : 'grid-cols-1'}`}>
        {panels.map((panel, idx) => (
          <PanelCard
            key={panel.id}
            idx={idx}
            panel={panel}
            datasets={datasets}
            colorIdx={idx}
            result={results[idx]}
            loading={loading}
            canRemove={panels.length > 1}
            dateCol={dateCol}
            userCol={userCol}
            period={period}
            onUpdate={patch => updatePanel(idx, patch)}
            onRemove={() => removePanel(idx)}
          />
        ))}
      </div>
    </div>
  )
}
