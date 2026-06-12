import { useState, useEffect } from 'react'
import { Users, Filter, Code2 } from 'lucide-react'
import type { DatasetInfo, QualityResult } from '../../types'
import { runCohort, fetchColumnValues, type CohortResult } from '../../api/ml'
import DataQualityBanner from './DataQualityBanner'
import { cellBg, cellText, type Period } from './cohortUtils'
import CohortCompareView from './CohortCompareView'
import CodePanel from './CodePanel'
import { MSG } from '../../messages'

interface Props { dataset: DatasetInfo; datasets: DatasetInfo[]; quality: QualityResult | null; qualityError?: boolean }

export default function MlCohortView({ dataset, datasets, quality, qualityError }: Props) {
  const [mode, setMode] = useState<'single' | 'compare'>('single')

  const cols = dataset.columns.map(c => c.name)

  const defaultDate = cols.find(c => /date|time|day|month|period|cohort/i.test(c)) ?? cols[0] ?? ''
  const defaultUser = cols.find(c => c !== defaultDate && /id|user|cust|key/i.test(c))
    ?? cols.find(c => c !== defaultDate)
    ?? cols[0] ?? ''

  // Auto-detect pre-aggregated mode: look for offset and metric columns
  const defaultOffset = cols.find(c => /index|offset|period_num|cohort_index/i.test(c) && c !== defaultDate) ?? ''
  const defaultMetric = cols.find(c => /luot|amount|value|metric|count|sum|tich/i.test(c) && c !== defaultDate && c !== defaultOffset) ?? ''

  const [userCol,    setUserCol]    = useState(defaultUser)
  const [dateCol,    setDateCol]    = useState(defaultDate)
  const [period,     setPeriod]     = useState<Period>('month')
  const [filterCol,  setFilterCol]  = useState('')
  const [filterVal,  setFilterVal]  = useState('')
  const [filterOpts, setFilterOpts] = useState<string[]>([])
  const [offsetCol,  setOffsetCol]  = useState(defaultOffset)
  const [metricCol,  setMetricCol]  = useState(defaultMetric)
  const [loading,    setLoading]    = useState(false)
  const [error,      setError]      = useState('')
  const [result,     setResult]     = useState<CohortResult | null>(null)
  const [showCode,   setShowCode]   = useState(false)

  // Load unique values when filter column changes
  useEffect(() => {
    if (!filterCol) { setFilterOpts([]); setFilterVal(''); return }
    fetchColumnValues(dataset.file_id, filterCol)
      .then(vals => { setFilterOpts(vals); setFilterVal(vals[0] ?? '') })
      .catch(() => setFilterOpts([]))
  }, [filterCol, dataset.file_id])

  const preAggMode = !!(offsetCol && metricCol)

  async function handleRun() {
    setLoading(true); setError(''); setResult(null)
    try {
      setResult(await runCohort(
        dataset.file_id, dateCol, userCol, period,
        filterCol || undefined, filterVal || undefined,
        offsetCol || undefined, metricCol || undefined,
      ))
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail ?? MSG.cohortFailed)
    } finally { setLoading(false) }
  }

  const periodLabel = (n: number) => {
    if (period === 'day')     return `Day ${n}`
    if (period === 'week')    return `Wk ${n}`
    if (period === 'quarter') return `Q ${n}`
    if (period === 'year')    return `Yr ${n}`
    return `Mo ${n}`
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Mode toggle */}
      <div className="flex items-center gap-2 px-4 pt-3 pb-0 flex-shrink-0">
        <div className="flex bg-[#161b22] rounded-md p-0.5 gap-0.5">
          {(['single', 'compare'] as const).map(m => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-3 py-1 rounded text-[11px] font-medium transition-all capitalize ${
                mode === m
                  ? 'bg-data/10 text-data border border-data/30'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {m === 'single' ? 'Single' : '⇄ Compare'}
            </button>
          ))}
        </div>
        {mode === 'compare' && (
          <span className="text-[10px] text-gray-600">Compare up to 3 segments or datasets</span>
        )}
      </div>

      {mode === 'compare' ? (
        <CohortCompareView dataset={dataset} datasets={datasets} quality={quality} qualityError={qualityError} />
      ) : (
        <>
          <DataQualityBanner quality={quality} qualityError={qualityError} />
          <div className="flex flex-col gap-4 p-4 flex-1 overflow-auto">
      {/* Controls */}
      <div className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-[10px] text-gray-500 mb-1">Cohort column</label>
          <select className="input-base text-xs" value={dateCol} onChange={e => setDateCol(e.target.value)}>
            {cols.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        {/* Pre-aggregated: offset + metric columns */}
        <div>
          <label className="block text-[10px] text-gray-500 mb-1">Period index col <span className="text-gray-700">(0,1,2…)</span></label>
          <select className="input-base text-xs" value={offsetCol} onChange={e => setOffsetCol(e.target.value)}>
            <option value="">— none —</option>
            {cols.filter(c => c !== dateCol).map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        <div>
          <label className="block text-[10px] text-gray-500 mb-1">Value col <span className="text-gray-700">(SUM)</span></label>
          <select className="input-base text-xs" value={metricCol} onChange={e => setMetricCol(e.target.value)}>
            <option value="">— none —</option>
            {cols.filter(c => c !== dateCol && c !== offsetCol).map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        {/* Transactional mode extras (shown only when not pre-agg) */}
        {!preAggMode && (
          <>
            <div>
              <label className="block text-[10px] text-gray-500 mb-1">ID / Count col</label>
              <select className="input-base text-xs" value={userCol} onChange={e => setUserCol(e.target.value)}>
                {cols.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>

            <div>
              <label className="block text-[10px] text-gray-500 mb-1">Period</label>
              <div className="flex gap-1">
                {(['day','week','month','quarter','year'] as Period[]).map(p => (
                  <button key={p} onClick={() => setPeriod(p)}
                    className={`px-2 py-1 rounded text-[11px] border transition-all capitalize ${
                      period === p
                        ? 'bg-data/10 text-data border-data/30'
                        : 'text-gray-500 border-transparent hover:text-gray-300'
                    }`}
                  >{p}</button>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Filter by dimension */}
        <div className="flex items-end gap-2 border-l border-white/10 pl-3">
          <div>
            <label className="block text-[10px] text-gray-500 mb-1 flex items-center gap-1">
              <Filter size={9} /> Filter by
            </label>
            <select
              className="input-base text-xs"
              value={filterCol}
              onChange={e => { setFilterCol(e.target.value); setFilterVal('') }}
            >
              <option value="">— none —</option>
              {cols.filter(c => c !== userCol && c !== dateCol).map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          {filterCol && filterOpts.length > 0 && (
            <div>
              <label className="block text-[10px] text-gray-500 mb-1">Value</label>
              <select className="input-base text-xs" value={filterVal} onChange={e => setFilterVal(e.target.value)}>
                {filterOpts.map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
          )}
        </div>

        <button
          onClick={handleRun}
          disabled={loading || !dateCol || (!preAggMode && !userCol)}
          className="px-3 py-1.5 bg-data/10 hover:bg-data/20 text-data border border-data/20 rounded text-xs font-medium transition-all disabled:opacity-40 flex items-center gap-1.5"
        >
          {loading
            ? <><span className="w-3 h-3 border border-data border-t-transparent rounded-full animate-spin" /> Running…</>
            : <><Users size={12} /> Compute</>}
        </button>
      </div>

      {/* Active filter badge */}
      {filterCol && filterVal && (
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-500">Showing:</span>
          <span className="text-[11px] bg-data/10 text-data border border-data/20 px-2 py-0.5 rounded-full">
            {filterCol} = {filterVal}
          </span>
          <button onClick={() => { setFilterCol(''); setFilterVal('') }}
            className="text-[10px] text-gray-600 hover:text-gray-400">✕ clear</button>
        </div>
      )}

      {error && <p className="text-danger text-xs">{error}</p>}

      {result && result.suitable === false && (
        <div className="p-4 rounded-lg border border-amber-500/30 bg-amber-500/5">
          <p className="text-amber-400 text-sm font-semibold mb-2">
            Dữ liệu này chưa phù hợp cho phân tích Cohort
          </p>
          <ul className="list-disc pl-5 text-gray-400 text-xs space-y-1">
            {result.reasons?.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
          {result.needs && <p className="text-gray-500 text-[11px] mt-2">{result.needs}</p>}
        </div>
      )}

      {/* Retention table */}
      {result && result.suitable !== false && (
        <>
        <div className="overflow-auto rounded-lg border border-white/5">
          <table className="text-[11px] border-collapse w-full">
            <thead>
              <tr className="bg-[#0d1117]">
                <th className="sticky left-0 z-10 bg-[#0d1117] px-3 py-2 text-left text-gray-400 font-medium whitespace-nowrap border-b border-white/5">
                  Cohort
                </th>
                <th className="px-3 py-2 text-right text-gray-400 font-medium whitespace-nowrap border-b border-white/5">
                  {preAggMode ? (metricCol || 'Value') : 'Count'}
                </th>
                {result.periods.map(n => (
                  <th key={n} className="px-2 py-2 text-center text-gray-500 font-medium whitespace-nowrap border-b border-white/5 min-w-[52px]">
                    {periodLabel(n)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.cohorts.map((label, ri) => (
                <tr key={label} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                  <td className="sticky left-0 z-10 bg-[#0d1117] px-3 py-1.5 text-gray-300 font-medium whitespace-nowrap">
                    {label}
                  </td>
                  <td className="px-3 py-1.5 text-right text-gray-400 whitespace-nowrap">
                    {result.cohort_sizes[ri].toLocaleString()}
                  </td>
                  {result.matrix[ri].map((pct, ci) => (
                    <td
                      key={ci}
                      title={pct !== null ? `${pct}%` : undefined}
                      style={{ background: cellBg(pct, '59,130,246') }}
                      className={`px-2 py-1.5 text-center font-medium transition-colors ${cellText(pct)}`}
                    >
                      {pct !== null ? `${pct}%` : ''}
                    </td>
                  ))}
                </tr>
              ))}

              {result.all_users_row && (
                <tr className="border-t-2 border-white/10 bg-white/[0.03]">
                  <td className="sticky left-0 z-10 bg-[#161b22] px-3 py-2 text-white font-semibold whitespace-nowrap">
                    All Users
                  </td>
                  <td className="px-3 py-2 text-right text-gray-300 font-semibold whitespace-nowrap">
                    {(result.all_users_size ?? 0).toLocaleString()}
                  </td>
                  {result.all_users_row.map((pct, ci) => (
                    <td
                      key={ci}
                      title={pct !== null ? `${pct}%` : undefined}
                      style={{ background: cellBg(pct, '59,130,246') }}
                      className={`px-2 py-2 text-center font-semibold transition-colors ${cellText(pct)}`}
                    >
                      {pct !== null ? `${pct}%` : ''}
                    </td>
                  ))}
                </tr>
              )}
            </tbody>
          </table>

          <div className="flex items-center gap-2 px-3 py-2 border-t border-white/5">
            <span className="text-[10px] text-gray-600">Retention %</span>
            <div className="flex gap-0.5">
              {[0, 10, 20, 30, 40, 50, 65, 80, 100].map(v => (
                <div key={v} style={{ background: cellBg(v, '59,130,246'), width: 20, height: 10, borderRadius: 2 }} title={`${v}%`} />
              ))}
            </div>
            <span className="text-[10px] text-gray-600">0% → 100%</span>
            <span className="text-[10px] text-gray-600 ml-4">
              {result.cohorts.length} cohorts ·{' '}
              {preAggMode
                ? `Period 0 = base (${metricCol})`
                : `${period === 'day' ? 'Day' : period === 'week' ? 'Week' : period === 'quarter' ? 'Quarter' : period === 'year' ? 'Year' : 'Month'} 0 = first activity`}
            </span>
            <button
              onClick={() => setShowCode(o => !o)}
              className={`ml-auto flex items-center gap-1 text-[10px] transition-colors ${showCode ? 'text-analytics' : 'text-gray-600 hover:text-gray-400'}`}
            >
              <Code2 size={10} /> {showCode ? 'Hide Code' : 'Show Code'}
            </button>
          </div>
        </div>

        {showCode && (
          <CodePanel
            code={result?.code ?? ''}
            filename="cohort_analysis.py"
          />
        )}
        </>
      )}

      {!result && !loading && (
        <div className="flex flex-col items-center justify-center flex-1 gap-2 text-gray-600">
          <Users size={32} strokeWidth={1} />
          <p className="text-sm">Chọn Cohort column + cấu hình, rồi click Compute</p>
          <p className="text-xs text-gray-700">
            Đã có sẵn Period index + Value col? Chọn cả 2 để dùng Pre-aggregated mode (SUM thay vì COUNT DISTINCT).
          </p>
        </div>
      )}
          </div>
        </>
      )}
    </div>
  )
}
