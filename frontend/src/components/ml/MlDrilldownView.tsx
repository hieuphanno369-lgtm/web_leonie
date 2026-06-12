import { useEffect, useMemo, useRef, useState } from 'react'
import { Layers, ChevronRight, Download } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import type { DatasetInfo, DrilldownResult } from '../../types'
import { fetchDrilldown } from '../../api/ml'
import { type YScale, fmtY, fmtFull } from './numFormat'
import CodePanel from './CodePanel'
import { describeSeries } from './insights'
import { downloadSvgAsPng } from './chartExport'
import { MSG } from '../../messages'

interface Props { dataset: DatasetInfo }

type Level = 'year' | 'month' | 'day'
const AGGS = ['sum', 'mean', 'count', 'n_unique', 'min', 'max'] as const
const MONTH_LABEL = (m: number) => `Th${String(m).padStart(2, '0')}`

export default function MlDrilldownView({ dataset }: Props) {
  const [open, setOpen] = useState(false)

  // Column guesses (same heuristic as the time-series panel)
  const guess = useMemo(() => {
    const cols = dataset.columns
    const date =
      cols.find(c => /date|datetime|timestamp/i.test(c.dtype))?.name ??
      cols.find(c => /date|time|day|month|year|period|ngay|thang/i.test(c.name))?.name ??
      cols[0]?.name ?? ''
    const value =
      cols.find(c => /int|float|decimal|double/i.test(c.dtype) && c.name !== date)?.name ?? ''
    return { date, value }
  }, [dataset.file_id])  // eslint-disable-line react-hooks/exhaustive-deps

  const [dateCol, setDateCol] = useState(guess.date)
  const [valueCol, setValueCol] = useState(guess.value)
  const [agg, setAgg] = useState<string>('sum')
  const [level, setLevel] = useState<Level>('year')
  const [year, setYear] = useState<number | undefined>(undefined)
  const [month, setMonth] = useState<number | undefined>(undefined)
  const [res, setRes] = useState<DrilldownResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [scale, setScale] = useState<YScale>('auto')
  const [yearOpts, setYearOpts] = useState<number[]>([])
  const [monthOpts, setMonthOpts] = useState<string[]>([])  // "YYYY-MM" of the current year

  // Reset to root when the dataset or the picked columns change
  useEffect(() => {
    setDateCol(guess.date); setValueCol(guess.value)
    setLevel('year'); setYear(undefined); setMonth(undefined)
    setRes(null); setError(''); setYearOpts([]); setMonthOpts([])
  }, [dataset.file_id])  // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch whenever an input changes while the panel is open
  useEffect(() => {
    if (!open || !dateCol || !valueCol) return
    let alive = true
    setLoading(true); setError('')
    fetchDrilldown(dataset.file_id, dateCol, valueCol, agg, level, year, month)
      .then(r => {
        if (!alive) return
        setRes(r)
        if (level === 'year') setYearOpts(r.labels.map(Number).filter(n => !Number.isNaN(n)))
        if (level === 'month') setMonthOpts(r.labels)
      })
      .catch((e: unknown) => {
        if (alive) setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? MSG.drilldownFailed)
      })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [open, dataset.file_id, dateCol, valueCol, agg, level, year, month])

  const chartData = useMemo(
    () => (res?.labels ?? []).map((label, i) => ({ label, y: res!.values[i] ?? 0 })),
    [res],
  )
  const maxAbs = useMemo(
    () => Math.max(1, ...chartData.map(d => Math.abs(d.y))),
    [chartData],
  )
  const drillChartRef = useRef<HTMLDivElement>(null)

  function drillInto(label: string) {
    if (level === 'year') { setYear(Number(label)); setMonth(undefined); setLevel('month') }
    else if (level === 'month') { setMonth(Number(label.split('-')[1])); setLevel('day') }
    // day = leaf, no further drill
  }

  const tooltipStyle = { background: '#161b22', border: '1px solid rgba(255,255,255,0.1)', fontSize: 12 }
  const axisStyle = { fill: '#6b7280', fontSize: 10 }

  return (
    <div className="border border-white/5 rounded-lg overflow-hidden">
      <button onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-white/3 hover:bg-white/5 transition-colors text-left">
        <Layers size={12} className="text-gray-500" />
        <span className="text-[11px] font-medium text-gray-300">Khoan sâu thời gian</span>
        <span className="text-[10px] text-gray-600 ml-1">— Năm → Tháng → Ngày (bấm cột để khoan)</span>
      </button>

      {open && (
        <div className="p-3 flex flex-col gap-3">
          {/* Controls */}
          <div className="flex gap-2 flex-wrap items-end">
            <div>
              <label className="block text-[10px] text-gray-600 mb-1">Date field</label>
              <select className="input-base text-xs" value={dateCol} onChange={e => { setDateCol(e.target.value); setLevel('year'); setYear(undefined); setMonth(undefined) }}>
                <option value="">—</option>
                {dataset.columns.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-[10px] text-gray-600 mb-1">Value</label>
              <select className="input-base text-xs" value={valueCol} onChange={e => setValueCol(e.target.value)}>
                <option value="">—</option>
                {dataset.columns.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-[10px] text-gray-600 mb-1">Agg</label>
              <select className="input-base text-xs" value={agg} onChange={e => setAgg(e.target.value)}>
                {AGGS.map(a => <option key={a} value={a}>{a}</option>)}
              </select>
            </div>
            <div className="flex gap-0.5 pb-0.5 ml-auto">
              {(['auto', 'K', 'M', 'B', '%'] as YScale[]).map(s => (
                <button key={s} onClick={() => setScale(s)}
                  className={`px-1.5 py-1 rounded text-[10px] border transition-all ${
                    scale === s ? 'bg-work/10 text-work border-work/30' : 'text-gray-600 border-transparent hover:text-gray-400'
                  }`}>{s}</button>
              ))}
            </div>
          </div>

          {/* Breadcrumb — each crumb is a lateral dropdown */}
          <div className="flex items-center gap-1 text-[11px] text-gray-400 flex-wrap">
            <button
              onClick={() => { setLevel('year'); setYear(undefined); setMonth(undefined) }}
              className={`px-1.5 py-0.5 rounded hover:bg-white/5 ${level === 'year' ? 'text-work font-medium' : ''}`}>
              Tất cả
            </button>
            {year !== undefined && (
              <>
                <ChevronRight size={11} className="text-gray-600" />
                <select
                  className="bg-transparent border border-white/10 rounded px-1 py-0.5 text-[11px] text-gray-300"
                  value={year}
                  onChange={e => { setYear(Number(e.target.value)); setMonth(undefined); setLevel('month') }}>
                  {yearOpts.map(y => <option key={y} value={y}>{y}</option>)}
                </select>
              </>
            )}
            {month !== undefined && (
              <>
                <ChevronRight size={11} className="text-gray-600" />
                <select
                  className="bg-transparent border border-white/10 rounded px-1 py-0.5 text-[11px] text-gray-300"
                  value={month}
                  onChange={e => { setMonth(Number(e.target.value)); setLevel('day') }}>
                  {monthOpts.map(m => {
                    const mn = Number(m.split('-')[1])
                    return <option key={m} value={mn}>{MONTH_LABEL(mn)}</option>
                  })}
                </select>
              </>
            )}
          </div>

          {error && <p className="text-danger text-xs">{error}</p>}
          {loading && <p className="text-[11px] text-gray-500">Đang tính…</p>}

          {!loading && res && chartData.length > 0 && (
            <>
              <div ref={drillChartRef}>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={chartData} margin={{ top: 16, right: 8, bottom: 0, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="label" tick={axisStyle} />
                    <YAxis tickFormatter={(v) => fmtY(v, scale, maxAbs)} tick={axisStyle} width={52} />
                    <Tooltip contentStyle={tooltipStyle} formatter={(v) => [fmtFull(v as number), res.value_col]} />
                    <Bar
                      dataKey="y"
                      fill="#fbbf24"
                      radius={[3, 3, 0, 0]}
                      cursor={level === 'day' ? 'default' : 'pointer'}
                      onClick={(d) => { const p = d.payload as { label?: string } | undefined; if (p?.label) drillInto(p.label) }}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <button
                onClick={async () => {
                  const ok = await downloadSvgAsPng(drillChartRef.current?.querySelector('svg') ?? null, 'drilldown.png')
                  if (!ok) alert('Không xuất được PNG.')
                }}
                className="self-start flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-300 transition-colors">
                <Download size={11} /> PNG
              </button>
              {(() => {
                const ins = describeSeries(res.labels, res.values)
                return ins ? (
                  <p className="text-[11px] text-gray-400 bg-white/3 border border-white/5 rounded-md px-3 py-1.5">💡 {ins}</p>
                ) : null
              })()}
              <p className="text-[10px] text-gray-600">
                {level === 'day' ? 'Cấp ngày (chi tiết nhất)' : 'Bấm vào một cột để khoan sâu xuống cấp dưới'}
                {' · '}{res.agg}({res.value_col})
              </p>
              {res.code && <CodePanel code={res.code} filename="drilldown_pipeline.py" />}
            </>
          )}

          {!loading && res && chartData.length === 0 && (
            <p className="text-[11px] text-gray-600">Không có dữ liệu cho mốc thời gian này.</p>
          )}
        </div>
      )}
    </div>
  )
}
