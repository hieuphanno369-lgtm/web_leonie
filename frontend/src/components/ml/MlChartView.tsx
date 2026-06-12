import { useState, useMemo, useEffect, useRef } from 'react'
import { ArrowUpDown, Grid2x2, Users, TrendingUp, Link2, BarChart3, ScatterChart as ScatterIcon, ArrowUp, ArrowDown, AlertTriangle, RefreshCw, Download } from 'lucide-react'
import {
  BarChart, Bar, LabelList,
  LineChart, Line,
  AreaChart, Area,
  ScatterChart, Scatter,
  PieChart, Pie, Cell, Legend,
  Treemap,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import type { QueryResult, DatasetInfo, CorrelationMatrix, QualityResult, TimeseriesResult, ProfileResult } from '../../types'
import { fetchCorrelation, fetchProfile, runCohort, runTimeseries, type CohortResult } from '../../api/ml'
import { type YScale, fmtY, fmtFull } from './numFormat'
import CodePanel from './CodePanel'
import DataQualityBanner from './DataQualityBanner'
import CorrelationHeatmap from './CorrelationHeatmap'
import CorrelationRanked from './CorrelationRanked'
import MlDrilldownView from './MlDrilldownView'
import { buildRecipePool, type Recipe } from './chartRecipes'
import { describeSeries } from './insights'
import { downloadSvgAsPng } from './chartExport'
import { MSG } from '../../messages'

interface Props {
  result: QueryResult
  dataset: DatasetInfo | null
  quality: QualityResult | null
  qualityError?: boolean
}

type ChartType = 'bar' | 'line' | 'area' | 'scatter' | 'pie' | 'donut' | 'treemap' | 'clustered'
type SortDir   = 'none' | 'asc' | 'desc'

const CHART_TYPES: { key: ChartType; label: string }[] = [
  { key: 'bar',     label: 'Bar'     },
  { key: 'line',    label: 'Line'    },
  { key: 'area',    label: 'Area'    },
  { key: 'scatter', label: 'Scatter' },
  { key: 'pie',     label: 'Pie'     },
  { key: 'donut',   label: 'Donut'   },
  { key: 'treemap', label: 'Treemap' },
  { key: 'clustered', label: 'Cột nhóm' },
]

const PIE_COLORS = ['#60a5fa','#34d399','#f59e0b','#f87171','#a78bfa','#38bdf8','#fb923c','#4ade80']

const TS_GRAINS = ['auto', 'day', 'week', 'month', 'quarter', 'year'] as const
const TS_AGGS   = ['sum', 'mean', 'count', 'n_unique', 'min', 'max'] as const
const TS_COMPARISONS: { key: string; label: string }[] = [
  { key: 'yoy',        label: 'YoY' },
  { key: 'pop',        label: 'Kỳ trước' },
  { key: 'rolling',    label: 'TB trượt' },
  { key: 'cumulative', label: 'Lũy kế' },
]

// ── Smart column guesser ─────────────────────────────────────
function guessColumns(columns: string[], rows: unknown[][]) {
  // Skip Salesforce-style IDs: 15–18 alphanumeric chars starting with a digit
  const looksLikeSfId = (v: string) =>
    /^[a-zA-Z0-9]{15,18}$/.test(v) && /^\d/.test(v)

  let xGuess = columns[0] ?? ''
  for (const col of columns) {
    if (/^\s*id\s*$/i.test(col)) continue                          // skip col named "Id"
    const idx = columns.indexOf(col)
    const sample = rows.slice(0, 5).map(r => String(r[idx] ?? '')).filter(Boolean)
    if (!sample.length) continue
    if (sample.every(v => !isNaN(Number(v)))) continue             // skip purely numeric
    if (sample.every(v => looksLikeSfId(v))) continue              // skip SF IDs
    xGuess = col
    break
  }

  let yGuess = columns[Math.min(1, columns.length - 1)] ?? ''
  for (let i = columns.length - 1; i >= 0; i--) {
    const sample = rows.slice(0, 5).map(r => r[i]).filter(v => v !== null && v !== '')
    if (sample.length && sample.every(v => !isNaN(Number(v)))) {
      yGuess = columns[i]
      break
    }
  }
  return { xGuess, yGuess }
}

// ── Sort ────────────────────────────────────────────────────
function parseXSortKey(v: unknown): number {
  const s = String(v)
  const mY = s.match(/^(\d{1,2})-(\d{4})$/)
  if (mY) return parseInt(mY[2]) * 100 + parseInt(mY[1])
  const Ym = s.match(/^(\d{4})-(\d{1,2})$/)
  if (Ym) return parseInt(Ym[1]) * 100 + parseInt(Ym[2])
  const d = new Date(s)
  if (!isNaN(d.getTime())) return d.getTime()
  const n = Number(v); if (!isNaN(n)) return n
  return s.charCodeAt(0) ?? 0
}

// ── Cohort cell color — blue gradient (Day 0 = solid, others fade) ──
function cohortColor(pct: number | null, isDay0 = false): string {
  if (pct === null) return 'transparent'
  if (isDay0) return 'rgba(37, 99, 235, 0.85)'    // blue-700 solid
  const t = Math.min(pct / 100, 1)
  return `rgba(96, 165, 250, ${0.08 + t * 0.72})` // blue-400, opacity by retention
}
function cohortTextColor(pct: number | null, isDay0 = false): string {
  if (pct === null) return '#374151'
  if (isDay0 || pct > 40) return '#ffffff'
  if (pct > 15) return '#bfdbfe'
  return '#93c5fd'
}

// ── Max/Min custom dot ───────────────────────────────────────
function makeDot(maxY: number, minY: number, scale: YScale, maxAbs: number) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return function CustomDot(props: any) {
    const { cx, cy, payload } = props
    const isMax = payload.y === maxY, isMin = payload.y === minY
    if (!isMax && !isMin) return <circle cx={cx} cy={cy} r={2.5} fill="#60a5fa" />
    const color = isMax ? '#34d399' : '#f87171'
    return (
      <g>
        <circle cx={cx} cy={cy} r={5} fill={color} stroke="#0d1117" strokeWidth={1.5} />
        <text x={cx} y={cy + (isMax ? -12 : 14)} fill={color} fontSize={10}
          textAnchor="middle" fontWeight={600}>
          {fmtY(payload.y, scale, maxAbs)}
        </text>
      </g>
    )
  }
}

export default function MlChartView({ result, dataset, quality, qualityError }: Props) {
  const [xCol,    setXCol]    = useState(() => guessColumns(result.columns, result.rows).xGuess)
  const [yCol,    setYCol]    = useState(() => guessColumns(result.columns, result.rows).yGuess)
  const [type,    setType]    = useState<ChartType>('bar')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [yScale,  setYScale]  = useState<YScale>('auto')
  const [yMin,    setYMin]    = useState('')
  const [yMax,    setYMax]    = useState('')
  const [yCols,   setYCols]   = useState<string[]>([])

  // Correlation
  const [showCorr,    setShowCorr]    = useState(false)
  const [corrData,    setCorrData]    = useState<CorrelationMatrix | null>(null)
  const [corrLoading, setCorrLoading] = useState(false)
  const [corrError,   setCorrError]   = useState('')
  const corrFidRef = useRef<string | null>(null)

  // Reset corr state whenever the loaded file changes
  useEffect(() => {
    corrFidRef.current = null
    setCorrData(null)
    setCorrError('')
    setCorrLoading(false)
    setShowCorr(false)
  }, [dataset?.file_id])

  // Cohort
  const [showCohort,    setShowCohort]    = useState(false)
  const [cohortDate,    setCohortDate]    = useState(result.columns[0] ?? '')
  const [cohortUser,    setCohortUser]    = useState(result.columns[1] ?? result.columns[0] ?? '')
  const [cohortPeriod,  setCohortPeriod]  = useState<'day'|'week'|'month'>('day')
  const [cohortResult,  setCohortResult]  = useState<CohortResult | null>(null)
  const [cohortLoading, setCohortLoading] = useState(false)
  const [cohortError,   setCohortError]   = useState('')

  // Time series (server-side: dataset.columns + file_id → /ml/timeseries)
  const [showTs,    setShowTs]    = useState(false)
  const [tsDate,    setTsDate]    = useState('')
  const [tsValue,   setTsValue]   = useState('')
  const [tsGrain,   setTsGrain]   = useState<string>('auto')
  const [tsAgg,     setTsAgg]     = useState<string>('sum')
  const [tsComps,   setTsComps]   = useState<string[]>(['yoy', 'pop', 'rolling', 'cumulative'])
  const [tsResult,  setTsResult]  = useState<TimeseriesResult | null>(null)
  const [tsLoading, setTsLoading] = useState(false)
  const [tsError,   setTsError]   = useState('')
  const [tsScale,   setTsScale]   = useState<YScale>('auto')
  const tsPanelRef     = useRef<HTMLDivElement>(null)
  const cohortPanelRef = useRef<HTMLDivElement>(null)
  const chartWrapRef = useRef<HTMLDivElement>(null)

  // Pre-fill time-series pickers from the dataset schema; reset on file change
  useEffect(() => {
    setTsResult(null); setTsError(''); setShowTs(false)
    if (!dataset) { setTsDate(''); setTsValue(''); return }
    const cols = dataset.columns
    const dateGuess =
      cols.find(c => /date|datetime|timestamp/i.test(c.dtype))?.name ??
      cols.find(c => /date|time|day|month|year|period|ngay|thang/i.test(c.name))?.name ??
      cols[0]?.name ?? ''
    const numGuess =
      cols.find(c => /int|float|decimal|double/i.test(c.dtype) && c.name !== dateGuess)?.name ?? ''
    setTsDate(dateGuess); setTsValue(numGuess)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataset?.file_id])

  const data = useMemo(() => {
    const xIdx = result.columns.indexOf(xCol)
    const yIdx = result.columns.indexOf(yCol)
    let rows = result.rows.slice(0, 2000).map(row => ({
      x: row[xIdx], y: Number(row[yIdx]) || 0,
    }))
    const minV = yMin !== '' ? Number(yMin) : -Infinity
    const maxV = yMax !== '' ? Number(yMax) : Infinity
    if (yMin !== '' || yMax !== '') rows = rows.filter(r => r.y >= minV && r.y <= maxV)
    if (sortDir !== 'none') {
      rows = [...rows].sort((a,b) => {
        const ka = parseXSortKey(a.x), kb = parseXSortKey(b.x)
        return sortDir === 'asc' ? ka - kb : kb - ka
      })
    }
    return rows.slice(0, 500)
  }, [result, xCol, yCol, sortDir, yMin, yMax])

  // Columns in the current result that look numeric (sample-based), for clustered measures.
  const numericResultCols = useMemo(() => {
    const out: string[] = []
    result.columns.forEach((c, idx) => {
      const sample = result.rows.slice(0, 20).map(r => r[idx]).filter(v => v !== null && v !== '')
      if (sample.length && sample.every(v => !isNaN(Number(v)))) out.push(c)
    })
    return out
  }, [result])

  // Default the clustered measures to the first 2–3 numeric columns when empty / stale.
  useEffect(() => {
    setYCols(prev => {
      const valid = prev.filter(c => numericResultCols.includes(c))
      return valid.length ? valid : numericResultCols.slice(0, Math.min(3, numericResultCols.length))
    })
  }, [numericResultCols])

  const isClustered = type === 'clustered'

  const clusterData = useMemo(() => {
    if (!isClustered) return []
    const xIdx = result.columns.indexOf(xCol)
    const idxs = yCols.map(c => result.columns.indexOf(c))
    return result.rows.slice(0, 500).map(row => {
      const o: Record<string, unknown> = { x: row[xIdx] }
      yCols.forEach((c, k) => { o[c] = Number(row[idxs[k]]) || 0 })
      return o
    })
  }, [isClustered, result, xCol, yCols])

  const clusterMaxAbs = useMemo(() => {
    let m = 1
    clusterData.forEach(o => yCols.forEach(c => { m = Math.max(m, Math.abs(Number(o[c]) || 0)) }))
    return m
  }, [clusterData, yCols])

  const maxY   = useMemo(() => data.length ? Math.max(...data.map(d => d.y)) : 0, [data])
  const minY   = useMemo(() => data.length ? Math.min(...data.map(d => d.y)) : 0, [data])
  const maxAbs = useMemo(() => data.length ? Math.max(...data.map(d => Math.abs(d.y))) : 1, [data])

  const yTickFmt  = (v: number) => fmtY(v, yScale, maxAbs)
  const CustomDot = useMemo(() => makeDot(maxY, minY, yScale, maxAbs), [maxY, minY, yScale, maxAbs])

  const pieData = useMemo(() =>
    data.slice(0, 20).map(d => ({ name: String(d.x), value: Math.abs(d.y) }))
  , [data])

  const treemapData = useMemo(() =>
    data.slice(0, 50).map(d => ({ name: String(d.x), size: Math.abs(d.y) }))
  , [data])

  const tsMaxAbs = useMemo(
    () => Math.max(0, ...(tsResult?.series.values ?? []).map(v => Math.abs(v ?? 0))),
    [tsResult],
  )

  const isXY = !['pie','donut','treemap'].includes(type)

  const chartInsight = useMemo(
    () => (isXY ? describeSeries(data.map(d => String(d.x)), data.map(d => d.y)) : ''),
    [isXY, data],
  )

  const treemapUniqueCount = useMemo(() =>
    type === 'treemap' ? new Set(treemapData.map(d => d.name)).size : 0
  , [type, treemapData])

  async function handleCorrToggle() {
    if (showCorr) { setShowCorr(false); return }
    setShowCorr(true)
    if ((corrData || !dataset) && !corrError) return   // already loaded — just expand; but always retry on error
    const fid = dataset!.file_id
    corrFidRef.current = fid
    setCorrLoading(true); setCorrError('')
    try {
      const result = await fetchCorrelation(fid)
      if (corrFidRef.current === fid) setCorrData(result)
    } catch (e: unknown) {
      if (corrFidRef.current === fid)
        setCorrError(
          (e as { response?: { data?: { detail?: string } } })
            ?.response?.data?.detail ?? MSG.loadCorrelationFailed,
        )
    } finally {
      if (corrFidRef.current === fid) setCorrLoading(false)
    }
  }

  async function handleCohort() {
    if (!dataset) return
    setCohortLoading(true); setCohortError('')
    try {
      setCohortResult(await runCohort(dataset.file_id, cohortDate, cohortUser, cohortPeriod))
      requestAnimationFrame(() => cohortPanelRef.current?.scrollIntoView({ block: 'nearest' }))
    } catch (e: unknown) {
      setCohortError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? MSG.cohortFailed)
    } finally { setCohortLoading(false) }
  }

  async function handleTimeseries() {
    if (!dataset || !tsDate || !tsValue) return
    setTsLoading(true); setTsError('')
    try {
      const r = await runTimeseries(dataset.file_id, tsDate, tsValue, tsGrain, tsAgg, tsComps)
      setTsResult(r)
      requestAnimationFrame(() => tsPanelRef.current?.scrollIntoView({ block: 'nearest' }))
    } catch (e: unknown) {
      setTsError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? MSG.timeseriesFailed)
    } finally { setTsLoading(false) }
  }

  const [profile, setProfile] = useState<ProfileResult | null>(null)

  useEffect(() => {
    if (!dataset) { setProfile(null); return }
    fetchProfile(dataset.file_id).then(setProfile).catch(() => setProfile(null))
  }, [dataset?.file_id])

  const RECIPE_ICONS = { TrendingUp, Link2, BarChart3, ScatterChart: ScatterIcon, Grid2x2 }
  const RECIPE_WINDOW = 4

  const recipePool = useMemo(
    () => buildRecipePool(profile, result.columns),
    [profile, result.columns],
  )
  const [poolOffset, setPoolOffset] = useState(0)

  const visibleRecipes = useMemo(() => {
    if (!recipePool.length) return []
    const n = Math.min(RECIPE_WINDOW, recipePool.length)
    return Array.from({ length: n }, (_, k) => recipePool[(poolOffset + k) % recipePool.length])
  }, [recipePool, poolOffset])

  function applyRecipe(r: Recipe) {
    switch (r.kind) {
      case 'timeseries':
        setShowTs(true)
        if (r.x) setTsDate(r.x)
        if (r.y) setTsValue(r.y)
        setTsGrain('auto')
        break
      case 'correlation':
        if (!showCorr) handleCorrToggle()
        break
      case 'bar':
        setShowTs(false)
        if (r.x) setXCol(r.x)
        if (r.y) setYCol(r.y)
        setType('bar')
        break
      case 'scatter':
        setShowTs(false)
        if (r.x) setXCol(r.x)
        if (r.y) setYCol(r.y)
        setType('scatter')
        break
      case 'clustered':
        if (r.x) setXCol(r.x)
        if (r.ys) setYCols(r.ys)
        setType('clustered')
        break
    }
  }

  const tooltipStyle = { background: '#161b22', border: '1px solid rgba(255,255,255,0.1)', fontSize: 12 }
  const axisStyle    = { fill: '#6b7280', fontSize: 10 }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <DataQualityBanner quality={quality} qualityError={qualityError} />
      <div className="flex flex-col gap-3 p-4 flex-1 overflow-auto">
      {visibleRecipes.length > 0 && (
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-[10px] text-gray-500">Gợi ý biểu đồ:</span>
          {visibleRecipes.map((rec, i) => {
            const Icon = RECIPE_ICONS[rec.iconName]
            return (
              <button key={`${poolOffset}-${i}`} onClick={() => applyRecipe(rec)}
                className="px-2 py-1 rounded text-[10px] border border-blue-500/30 text-blue-400 hover:bg-blue-600/20 transition-all flex items-center gap-1">
                <Icon size={11} /> {rec.title}
              </button>
            )
          })}
          {recipePool.length > RECIPE_WINDOW && (
            <button
              onClick={() => setPoolOffset(o => (o + RECIPE_WINDOW) % recipePool.length)}
              title="Xem bộ gợi ý khác"
              className="px-2 py-1 rounded text-[10px] border border-white/15 text-gray-400 hover:text-gray-200 hover:bg-white/5 transition-all flex items-center gap-1">
              <RefreshCw size={11} /> Góc nhìn khác
            </button>
          )}
        </div>
      )}
      {/* Controls */}
      <div className="flex gap-2 flex-wrap items-end">
        {isXY && (
          <>
            <div>
              <label className="block text-[10px] text-gray-600 mb-1">X axis</label>
              <select className="input-base text-xs" value={xCol} onChange={e => setXCol(e.target.value)}>
                {result.columns.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            {!isClustered && (
              <div>
                <label className="block text-[10px] text-gray-600 mb-1">Y axis</label>
                <select className="input-base text-xs" value={yCol} onChange={e => setYCol(e.target.value)}>
                  {result.columns.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            )}
            {isClustered && (
              <div>
                <label className="block text-[10px] text-gray-600 mb-1">Measures (cột số)</label>
                <div className="flex gap-1 flex-wrap max-w-[360px]">
                  {numericResultCols.map(c => {
                    const on = yCols.includes(c)
                    return (
                      <button key={c}
                        onClick={() => setYCols(prev => on ? prev.filter(x => x !== c) : [...prev, c])}
                        className={`px-2 py-1 rounded text-[10px] border transition-all ${
                          on ? 'bg-data/10 text-data border-data/30' : 'text-gray-500 border-white/10 hover:text-gray-300'
                        }`}>{c}</button>
                    )
                  })}
                  {numericResultCols.length === 0 && (
                    <span className="text-[10px] text-gray-600">Không có cột số trong kết quả.</span>
                  )}
                </div>
              </div>
            )}
          </>
        )}
        {!isXY && (
          <>
            <div>
              <label className="block text-[10px] text-gray-600 mb-1">Label column</label>
              <select className="input-base text-xs" value={xCol} onChange={e => setXCol(e.target.value)}>
                {result.columns.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-[10px] text-gray-600 mb-1">Value column</label>
              <select className="input-base text-xs" value={yCol} onChange={e => setYCol(e.target.value)}>
                {result.columns.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </>
        )}

        {/* Chart type */}
        <div className="flex gap-1 pb-0.5 flex-wrap">
          {CHART_TYPES.map(t => (
            <button key={t.key} onClick={() => setType(t.key)}
              className={`px-2 py-1 rounded text-[11px] border transition-all ${
                type === t.key
                  ? 'bg-data/10 text-data border-data/30'
                  : 'text-gray-500 border-transparent hover:text-gray-300'
              }`}>{t.label}</button>
          ))}
        </div>

        {isXY && (
          <>
            <button onClick={() => setSortDir(d => d==='asc'?'desc':d==='desc'?'none':'asc')}
              className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] border transition-all ${
                sortDir !== 'none'
                  ? 'bg-analytics/10 text-analytics border-analytics/30'
                  : 'text-gray-500 border-transparent hover:text-gray-300'
              }`}>
              <ArrowUpDown size={11} />
              {sortDir==='asc'?'A→Z':sortDir==='desc'?'Z→A':'Sort'}
            </button>

            <div className="flex gap-0.5 pb-0.5">
              {(['auto','K','M','B','%'] as YScale[]).map(s => (
                <button key={s} onClick={() => setYScale(s)}
                  className={`px-1.5 py-1 rounded text-[10px] border transition-all ${
                    yScale===s ? 'bg-work/10 text-work border-work/30' : 'text-gray-600 border-transparent hover:text-gray-400'
                  }`}>{s}</button>
              ))}
            </div>

            <div className="flex items-center gap-1 pb-0.5">
              <label className="text-[10px] text-gray-600">Y:</label>
              <input type="number" placeholder="min" value={yMin}
                onChange={e => setYMin(e.target.value)}
                className="input-base text-xs w-16 py-1" />
              <span className="text-gray-600 text-[10px]">–</span>
              <input type="number" placeholder="max" value={yMax}
                onChange={e => setYMax(e.target.value)}
                className="input-base text-xs w-16 py-1" />
            </div>
          </>
        )}

      </div>

      {/* Treemap cardinality warning */}
      {type === 'treemap' && treemapUniqueCount > 15 && (
        <div className="flex flex-col gap-1 text-[11px] bg-yellow-500/5 border border-yellow-500/20 rounded-lg px-3 py-2.5">
          <span className="text-yellow-400 font-medium">
            <AlertTriangle size={12} className="inline mr-1" />{treemapUniqueCount} nhãn unique — treemap hiệu quả nhất với dữ liệu đã gộp (5–20 categories)
          </span>
          <span className="text-gray-500">
            Thử chạy query: <code className="font-mono text-yellow-300/70">
              SELECT {xCol}, SUM({yCol}) as total FROM data GROUP BY {xCol} ORDER BY total DESC
            </code>
          </span>
        </div>
      )}

      {isClustered && yCols.length > 6 && (
        <div className="text-[11px] bg-yellow-500/5 border border-yellow-500/20 rounded-lg px-3 py-2.5 text-yellow-400">
          <AlertTriangle size={12} className="inline mr-1" />
          {yCols.length} measure — quá nhiều cột cạnh nhau sẽ khó đọc; nên chọn ≤ 6.
        </div>
      )}

      {/* Main chart */}
      <div ref={chartWrapRef} className="bg-secondary border border-white/5 rounded-lg p-3" style={{ height: 280 }}>
        <ResponsiveContainer width="100%" height="100%">
          {type === 'clustered' ? (
            <BarChart data={clusterData} margin={{ top: 20, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="x" tick={axisStyle} />
              <YAxis tickFormatter={(v) => fmtY(v, yScale, clusterMaxAbs)} tick={axisStyle} width={52} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v, n) => [fmtFull(v as number), n as string]} />
              <Legend wrapperStyle={{ fontSize: 10, color: '#6b7280' }} />
              {yCols.map((c, i) => (
                <Bar key={c} dataKey={c} fill={PIE_COLORS[i % PIE_COLORS.length]} radius={[2, 2, 0, 0]} />
              ))}
            </BarChart>
          ) : type === 'bar' ? (
            <BarChart data={data} margin={{ top: 20, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="x" tick={axisStyle} />
              <YAxis tickFormatter={yTickFmt} tick={axisStyle} width={52} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [fmtFull(v as number), yCol]} />
              <Bar dataKey="y" fill="#60a5fa" radius={[3,3,0,0]}>
                <LabelList dataKey="y" position="top" fontSize={9} fill="#9ca3af"
                  formatter={(v) => (v as number===maxY||v as number===minY) ? fmtY(v as number,yScale,maxAbs) : ''} />
              </Bar>
            </BarChart>
          ) : type === 'line' ? (
            <LineChart data={data} margin={{ top: 20, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="x" tick={axisStyle} />
              <YAxis tickFormatter={yTickFmt} tick={axisStyle} width={52} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [fmtFull(v as number), yCol]} />
              <Line type="monotone" dataKey="y" stroke="#60a5fa" strokeWidth={2}
                dot={<CustomDot />} activeDot={{ r: 5, fill: '#60a5fa' }} />
            </LineChart>
          ) : type === 'area' ? (
            <AreaChart data={data} margin={{ top: 20, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#60a5fa" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#60a5fa" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="x" tick={axisStyle} />
              <YAxis tickFormatter={yTickFmt} tick={axisStyle} width={52} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [fmtFull(v as number), yCol]} />
              <Area type="monotone" dataKey="y" stroke="#60a5fa" strokeWidth={2}
                fill="url(#areaGrad)" dot={<CustomDot />} activeDot={{ r: 5 }} />
            </AreaChart>
          ) : type === 'scatter' ? (
            <ScatterChart margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="x" name={xCol} tick={axisStyle} />
              <YAxis dataKey="y" name={yCol} tickFormatter={yTickFmt} tick={axisStyle} width={52} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [fmtFull(v as number), yCol]}
                cursor={{ strokeDasharray: '3 3' }} />
              <Scatter data={data} fill="#60a5fa" fillOpacity={0.7} />
            </ScatterChart>
          ) : type === 'pie' || type === 'donut' ? (
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                innerRadius={type==='donut' ? '50%' : 0}
                outerRadius="75%"
                label={({ name, percent }) => `${name} ${((percent ?? 0)*100).toFixed(1)}%`}
                labelLine={{ stroke: '#4b5563' }}>
                {pieData.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [fmtFull(v as number), yCol]} />
              <Legend wrapperStyle={{ fontSize: 10, color: '#6b7280' }} />
            </PieChart>
          ) : (
            /* Treemap */
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            <Treemap data={treemapData} dataKey="size" nameKey="name"
              {...({ stroke: "#0d1117", strokeWidth: 2 } as any)}
              content={({ x, y, width, height, name, value, index }: any) => {
                const w = width ?? 0, h = height ?? 0
                const color = PIE_COLORS[(index ?? 0) % PIE_COLORS.length]
                return (
                  <g>
                    <rect x={x} y={y} width={w} height={h}
                      fill={color} fillOpacity={0.7} stroke="#0d1117" strokeWidth={2} rx={4} />
                    {w > 40 && h > 24 && (
                      <text x={(x??0)+w/2} y={(y??0)+h/2} textAnchor="middle"
                        dominantBaseline="middle" fill="#fff" fontSize={Math.min(11, w/6)}>
                        {String(name ?? '').length > 12 ? String(name ?? '').slice(0,10)+'…' : name}
                      </text>
                    )}
                    {w > 40 && h > 38 && (
                      <text x={(x??0)+w/2} y={(y??0)+h/2+13} textAnchor="middle"
                        dominantBaseline="middle" fill="rgba(255,255,255,0.6)" fontSize={9}>
                        {fmtY(value??0, yScale, maxAbs)}
                      </text>
                    )}
                  </g>
                )
              }}
            />
          )}
        </ResponsiveContainer>
      </div>

      <div className="flex items-center gap-4 text-[10px]">
        <span className="text-gray-600">
          {data.length} / {result.rows.length} rows · {result.duration_ms.toFixed(1)}ms · DuckDB
          {sortDir!=='none' && <span className="ml-2 text-analytics">sorted {sortDir}</span>}
        </span>
        {isXY && data.length > 0 && (
          <>
            <span className="text-green-400"><ArrowUp size={12} className="inline" /> max {fmtFull(maxY)}</span>
            <span className="text-red-400"><ArrowDown size={12} className="inline" /> min {fmtFull(minY)}</span>
          </>
        )}
        <button
          onClick={async () => {
            const ok = await downloadSvgAsPng(chartWrapRef.current?.querySelector('svg') ?? null, 'ml_chart.png')
            if (!ok) alert('Không xuất được PNG (thử lại hoặc dùng Copy CSV).')
          }}
          className="ml-auto flex items-center gap-1 text-gray-500 hover:text-gray-300 transition-colors">
          <Download size={12} /> PNG
        </button>
      </div>

      {chartInsight && (
        <p className="text-[11px] text-gray-400 bg-white/3 border border-white/5 rounded-md px-3 py-1.5">
          💡 {chartInsight}
        </p>
      )}

      {/* ── Cohort Analysis ──────────────────────────────────── */}
      {dataset && (
        <div className="border border-white/5 rounded-lg overflow-hidden">
          <button onClick={() => setShowCohort(o => !o)}
            className="w-full flex items-center gap-2 px-3 py-2 bg-white/3 hover:bg-white/5 transition-colors text-left">
            <Users size={12} className="text-gray-500" />
            <span className="text-[11px] font-medium text-gray-300">Cohort Retention</span>
            <span className="text-[10px] text-gray-600 ml-1">— retention % per period</span>
          </button>

          {showCohort && (
            <div className="p-3 flex flex-col gap-3">
              <div className="flex gap-2 flex-wrap items-end">
                <div>
                  <label className="block text-[10px] text-gray-600 mb-1">Date column</label>
                  <select className="input-base text-xs" value={cohortDate}
                    onChange={e => setCohortDate(e.target.value)}>
                    {result.columns.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-gray-600 mb-1">User / ID column</label>
                  <select className="input-base text-xs" value={cohortUser}
                    onChange={e => setCohortUser(e.target.value)}>
                    {result.columns.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div className="flex gap-1 pb-0.5">
                  {(['day','week','month'] as const).map(p => (
                    <button key={p} onClick={() => setCohortPeriod(p)}
                      className={`px-2 py-1 rounded text-[11px] border transition-all ${
                        cohortPeriod===p
                          ? 'bg-blue-600/20 text-blue-400 border-blue-500/30'
                          : 'text-gray-500 border-transparent hover:text-gray-300'
                      }`}>{p}</button>
                  ))}
                </div>
                <button onClick={handleCohort} disabled={cohortLoading}
                  className="btn-primary text-xs flex items-center gap-1.5 disabled:opacity-50">
                  <Users size={11} /> {cohortLoading ? 'Computing…' : 'Run Cohort'}
                </button>
              </div>

              {cohortError && <p className="text-danger text-xs">{cohortError}</p>}

              {cohortResult && cohortResult.suitable === false && (
                <div className="p-3 rounded-lg border border-amber-500/30 bg-amber-500/5">
                  <p className="text-amber-400 text-xs font-semibold mb-1">Dữ liệu chưa phù hợp cho Cohort</p>
                  <ul className="list-disc pl-4 text-gray-500 text-[10px] space-y-0.5">
                    {cohortResult.reasons?.map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </div>
              )}

              {cohortResult && cohortResult.suitable !== false && (
                <div ref={cohortPanelRef} className="overflow-auto rounded-lg border border-white/8">
                  {/* Legend */}
                  <div className="flex items-center justify-between px-3 py-2 bg-white/3 border-b border-white/5">
                    <div className="flex items-center gap-3 text-[10px] text-gray-500">
                      <span>
                        {cohortResult.cohorts.length} cohorts ·{' '}
                        {cohortResult.all_users_size?.toLocaleString() ?? '—'} users total
                      </span>
                      <span className="text-gray-700">|</span>
                      <span>
                        {cohortPeriod === 'day' ? 'Day 0 = first visit' :
                         cohortPeriod === 'week' ? 'Week 0 = acquisition' : 'Month 0 = acquisition'}
                        {' '}· empty = no data yet
                      </span>
                    </div>
                    {/* Blue gradient legend */}
                    <div className="flex items-center gap-1.5 text-[10px] text-gray-600">
                      <span>0%</span>
                      <div className="flex h-2.5 rounded overflow-hidden w-20">
                        {[0.08,0.2,0.35,0.5,0.65,0.8].map((o,i) => (
                          <div key={i} className="flex-1" style={{ background: `rgba(96,165,250,${o})` }} />
                        ))}
                      </div>
                      <span>100%</span>
                    </div>
                  </div>

                  <table className="border-collapse text-[11px] w-full">
                    <thead>
                      <tr className="bg-white/2">
                        <th className="text-left px-3 py-2 text-gray-500 font-normal whitespace-nowrap sticky left-0 bg-gray-950 z-10 border-r border-white/5">
                          Cohort
                        </th>
                        <th className="text-right px-3 py-2 text-gray-500 font-normal whitespace-nowrap border-r border-white/5">
                          Users
                        </th>
                        {cohortResult.periods.map(p => (
                          <th key={p} className="text-center px-1 py-2 text-gray-500 font-normal min-w-[52px]">
                            {cohortPeriod === 'day' ? `Day ${p}` : `+${p}`}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {cohortResult.cohorts.map((cohort, i) => (
                        <tr key={cohort} className="border-t border-white/4 hover:bg-white/1 transition-colors">
                          <td className="px-3 py-1.5 text-gray-300 whitespace-nowrap font-medium sticky left-0 bg-gray-950 border-r border-white/5">
                            {cohort}
                          </td>
                          <td className="px-3 py-1.5 text-right text-gray-500 tabular-nums border-r border-white/5">
                            {cohortResult.cohort_sizes[i].toLocaleString()}
                          </td>
                          {cohortResult.matrix[i].map((pct, j) => (
                            <td key={j} className="px-1 py-1.5 text-center font-semibold tabular-nums min-w-[52px] h-8"
                              style={{
                                background: cohortColor(pct, j === 0),
                                color: cohortTextColor(pct, j === 0),
                              }}>
                              {pct !== null ? `${pct}%` : ''}
                            </td>
                          ))}
                        </tr>
                      ))}

                      {/* All Users aggregate row */}
                      {cohortResult.all_users_row && (
                        <tr className="border-t-2 border-white/10 bg-white/3">
                          <td className="px-3 py-2 text-white font-bold whitespace-nowrap sticky left-0 bg-gray-900 border-r border-white/5">
                            All Users
                          </td>
                          <td className="px-3 py-2 text-right text-gray-300 font-bold tabular-nums border-r border-white/5">
                            {cohortResult.all_users_size?.toLocaleString() ?? '—'}
                          </td>
                          {cohortResult.all_users_row.map((pct, j) => (
                            <td key={j} className="px-1 py-2 text-center font-bold tabular-nums min-w-[52px]"
                              style={{
                                background: cohortColor(pct, j === 0),
                                color: cohortTextColor(pct, j === 0),
                              }}>
                              {pct !== null ? `${pct}%` : ''}
                            </td>
                          ))}
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Correlation Heatmap ──────────────────────────────── */}
      {dataset && (
        <div className="border border-white/5 rounded-lg overflow-hidden">
          <button
            onClick={handleCorrToggle}
            aria-expanded={showCorr}
            className="w-full flex items-center gap-2 px-3 py-2 bg-white/3 hover:bg-white/5 transition-colors text-left"
          >
            <Grid2x2 size={12} className="text-gray-500" />
            <span className="text-[11px] font-medium text-gray-300">Correlation Heatmap</span>
            <span className="text-[10px] text-gray-600 ml-1">— Pearson, numeric columns only</span>
          </button>

          {showCorr && (
            <div className="p-3">
              {corrLoading
                ? <p className="text-[11px] text-gray-500">Computing…</p>
                : corrError
                  ? <p className="text-[11px] text-danger">{corrError}</p>
                  : corrData
                    ? (
                      <>
                        <CorrelationHeatmap data={corrData} />
                        <CorrelationRanked data={corrData} />
                        {corrData.code && <CodePanel code={corrData.code} filename="correlation_pipeline.py" />}
                      </>
                    )
                    : null}
            </div>
          )}
        </div>
      )}

      {/* ── Khoan sâu thời gian (drill-down) ─────────────────── */}
      {dataset && <MlDrilldownView dataset={dataset} />}

      {/* ── Chuỗi thời gian ──────────────────────────────────── */}
      {dataset && (
        <div className="border border-white/5 rounded-lg overflow-hidden">
          <button onClick={() => setShowTs(o => !o)}
            className="w-full flex items-center gap-2 px-3 py-2 bg-white/3 hover:bg-white/5 transition-colors text-left">
            <TrendingUp size={12} className="text-gray-500" />
            <span className="text-[11px] font-medium text-gray-300">Chuỗi thời gian</span>
            <span className="text-[10px] text-gray-600 ml-1">— gộp ngày/tuần/tháng/quý/năm + YoY/kỳ trước</span>
          </button>

          {showTs && (
            <div className="p-3 flex flex-col gap-3">
              <div className="flex gap-2 flex-wrap items-end">
                <div>
                  <label className="block text-[10px] text-gray-600 mb-1">Date column</label>
                  <select className="input-base text-xs" value={tsDate} onChange={e => setTsDate(e.target.value)}>
                    <option value="">—</option>
                    {dataset.columns.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-gray-600 mb-1">Value column</label>
                  <select className="input-base text-xs" value={tsValue} onChange={e => setTsValue(e.target.value)}>
                    <option value="">—</option>
                    {dataset.columns.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-gray-600 mb-1">Grain</label>
                  <select className="input-base text-xs" value={tsGrain} onChange={e => setTsGrain(e.target.value)}>
                    {TS_GRAINS.map(g => <option key={g} value={g}>{g}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-gray-600 mb-1">Agg</label>
                  <select className="input-base text-xs" value={tsAgg} onChange={e => setTsAgg(e.target.value)}>
                    {TS_AGGS.map(a => <option key={a} value={a}>{a}</option>)}
                  </select>
                </div>
                <div className="flex gap-1 pb-0.5">
                  {TS_COMPARISONS.map(c => (
                    <button key={c.key}
                      onClick={() => setTsComps(prev => prev.includes(c.key) ? prev.filter(x => x !== c.key) : [...prev, c.key])}
                      className={`px-2 py-1 rounded text-[11px] border transition-all ${
                        tsComps.includes(c.key)
                          ? 'bg-blue-600/20 text-blue-400 border-blue-500/30'
                          : 'text-gray-500 border-transparent hover:text-gray-300'
                      }`}>{c.label}</button>
                  ))}
                </div>
                <button onClick={handleTimeseries} disabled={tsLoading || !tsDate || !tsValue}
                  className="btn-primary text-xs flex items-center gap-1.5 disabled:opacity-50">
                  <TrendingUp size={11} /> {tsLoading ? 'Computing…' : 'Run'}
                </button>
              </div>

              {tsError && <p className="text-danger text-xs">{tsError}</p>}

              <div ref={tsPanelRef} style={{ minHeight: tsResult || tsLoading ? 360 : 0 }}>
                {tsLoading && !tsResult && (
                  <div className="h-[320px] rounded-lg bg-white/3 animate-pulse flex items-center justify-center">
                    <span className="text-[11px] text-gray-500">Đang tính chuỗi thời gian…</span>
                  </div>
                )}
                {tsResult && (
                  <>
                    <p className="text-[10px] text-gray-500">
                      {tsResult.grain} · {tsResult.meta.periods} kỳ · gợi ý: {tsResult.meta.suggested_grain}
                    </p>
                    <div className="flex justify-end">
                      <div className="flex gap-0.5">
                        {(['auto', 'K', 'M', 'B', '%'] as YScale[]).map(s => (
                          <button key={s} onClick={() => setTsScale(s)}
                            className={`px-1.5 py-1 rounded text-[10px] border transition-all ${
                              tsScale === s ? 'bg-work/10 text-work border-work/30' : 'text-gray-600 border-transparent hover:text-gray-400'
                            }`}>{s}</button>
                        ))}
                      </div>
                    </div>
                    <ResponsiveContainer width="100%" height={320}>
                      <LineChart data={tsResult.series.labels.map((label, i) => ({
                        label,
                        value:      tsResult.series.values[i],
                        yoy:        tsResult.comparisons.yoy?.values[i] ?? null,
                        pop:        tsResult.comparisons.pop?.values[i] ?? null,
                        rolling:    tsResult.comparisons.rolling?.values[i] ?? null,
                        cumulative: tsResult.comparisons.cumulative?.values[i] ?? null,
                      }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                        <XAxis dataKey="label" tick={axisStyle} />
                        <YAxis tick={axisStyle} tickFormatter={(v) => fmtY(v, tsScale, tsMaxAbs)} width={52} />
                        <Tooltip contentStyle={tooltipStyle} formatter={(v) => fmtFull(v as number)} />
                        <Legend wrapperStyle={{ fontSize: 10 }} />
                        <Line type="monotone" dataKey="value" stroke="#3b82f6" dot={false} name={tsResult.value_col} />
                        {tsResult.comparisons.yoy        && <Line type="monotone" dataKey="yoy"        stroke="#a855f7" strokeDasharray="4 2" dot={false} name="YoY" />}
                        {tsResult.comparisons.pop        && <Line type="monotone" dataKey="pop"        stroke="#f59e0b" strokeDasharray="4 2" dot={false} name="Kỳ trước" />}
                        {tsResult.comparisons.rolling    && <Line type="monotone" dataKey="rolling"    stroke="#22c55e" dot={false} name="TB trượt" />}
                        {tsResult.comparisons.cumulative && <Line type="monotone" dataKey="cumulative" stroke="#eab308" dot={false} name="Lũy kế" />}
                      </LineChart>
                    </ResponsiveContainer>
                    {(() => {
                      const ins = describeSeries(tsResult.series.labels, tsResult.series.values)
                      return ins ? (
                        <p className="text-[11px] text-gray-400 bg-white/3 border border-white/5 rounded-md px-3 py-1.5 mt-1">💡 {ins}</p>
                      ) : null
                    })()}
                    {tsResult.code && <CodePanel code={tsResult.code} filename="timeseries_pipeline.py" />}
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}
      </div>
    </div>
  )
}
