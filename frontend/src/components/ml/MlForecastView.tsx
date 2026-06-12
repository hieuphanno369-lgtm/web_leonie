import { useState, useMemo } from 'react'
import { TrendingUp, Download, BarChart2, Sparkles, Code2, Star, Check, X, AlertTriangle } from 'lucide-react'
import CodePanel from './CodePanel'
import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import type { DatasetInfo, ForecastResult, ForecastCompareResult, ForecastInterpretResult, QualityResult } from '../../types'
import { runForecast, compareForecast, interpretForecast } from '../../api/ml'
import { type YScale, fmtY, fmtFull } from './numFormat'
import DataQualityBanner from './DataQualityBanner'
import { MSG } from '../../messages'

interface Props { dataset: DatasetInfo; quality: QualityResult | null; qualityError?: boolean }

type ForecastMethod = 'linear' | 'moving_average' | 'ets' | 'sarimax' | 'supervised'

interface MethodMeta {
  value: ForecastMethod
  label: string
  group: string
  what: string
  when: string
  requires: string
  output: string
  needsSeasonal?: boolean
}

const METHODS: MethodMeta[] = [
  {
    value: 'linear',
    label: 'Linear Trend',
    group: 'Statistical',
    what: 'Dùng hồi quy tuyến tính OLS để fit đường thẳng qua toàn bộ dữ liệu, rồi kéo dài về tương lai.',
    when: 'Dữ liệu có xu hướng tăng/giảm đều đặn, không có mùa vụ rõ ràng. VD: doanh thu tăng trưởng steady.',
    requires: 'Tối thiểu 2 điểm dữ liệu. Hoạt động tốt nhất khi trend tuyến tính.',
    output: 'slope (tốc độ thay đổi mỗi kỳ), 95% CI dựa trên std của toàn chuỗi.',
  },
  {
    value: 'moving_average',
    label: 'Moving Average',
    group: 'Statistical',
    what: 'Tính rolling mean trên cửa sổ gần nhất, dùng slope của MA để dự báo. Giảm nhiễu tốt hơn linear.',
    when: 'Dữ liệu nhiều biến động (noisy), muốn dự báo bám sát xu hướng gần đây hơn là toàn chuỗi.',
    requires: 'Tối thiểu 6 điểm. Window size = min(7, n÷3) — tự động điều chỉnh.',
    output: 'slope của MA, 95% CI dựa trên std cục bộ (window gần nhất × 2).',
  },
  {
    value: 'ets',
    label: 'ETS (Holt-Winters)',
    group: 'Statistical (Seasonal)',
    what: 'Exponential Smoothing — tự động học trọng số cho level, trend, và seasonality theo thời gian.',
    when: 'Dữ liệu có trend + seasonality rõ. Nhanh hơn SARIMAX, ít over-fit hơn. Tốt với monthly/quarterly.',
    requires: 'Tối thiểu 2× seasonal_period điểm. statsmodels có sẵn, không cần cài thêm.',
    output: 'AIC (thấp = tốt hơn), alpha (level), beta (trend), gamma (seasonal).',
    needsSeasonal: true,
  },
  {
    value: 'sarimax',
    label: 'SARIMAX',
    group: 'Statistical (Seasonal)',
    what: 'Seasonal ARIMA — mô hình hoá cả trend, autocorrelation, và mùa vụ (seasonality) trong cùng một framework.',
    when: 'Dữ liệu có mùa vụ rõ (doanh số cao T12, thấp T2...). Tốt nhất cho time series đủ dài (≥ 2 mùa).',
    requires: 'Tối thiểu 2× seasonal_period điểm. VD: monthly data cần ≥ 24 tháng. Chọn đúng seasonal period.',
    output: 'Dự báo + 95% CI chính xác hơn. AIC để đánh giá độ fit (thấp hơn = tốt hơn).',
    needsSeasonal: true,
  },
  {
    value: 'supervised',
    label: 'Supervised (ML)',
    group: 'Machine Learning',
    what: 'Dùng Ridge Regression với lag features: giá trị tại t-1, t-2, ... t-k làm input để dự báo t+1. Recursive multi-step.',
    when: 'Chuỗi có autocorrelation cao (giá trị gần nhau tương quan mạnh). VD: tồn kho, traffic, engagement.',
    requires: 'Tối thiểu 20 điểm dữ liệu. Số lag = min(5, n÷4). Kém chính xác hơn SARIMA với dữ liệu seasonal.',
    output: 'R² (độ fit trên training data), số lag dùng, 95% CI từ residuals.',
  },
]

const SEASONAL_PRESETS = [
  { label: '7 (hàng tuần)', value: 7 },
  { label: '12 (hàng tháng)', value: 12 },
  { label: '4 (hàng quý)', value: 4 },
  { label: '52 (hàng năm/tuần)', value: 52 },
]

function downloadCsv(result: ForecastResult, valueCol: string) {
  const rows: string[] = ['date,value,lower_95,upper_95']
  for (const f of result.forecast) {
    rows.push(`${f.date},${f.value},${f.lower ?? ''},${f.upper ?? ''}`)
  }
  const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `forecast_${valueCol}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export default function MlForecastView({ dataset, quality, qualityError }: Props) {
  const cols = dataset.columns.map(c => c.name)
  const [dateCol,       setDateCol]       = useState(cols[0] ?? '')
  const [valueCol,      setValueCol]      = useState(cols[1] ?? '')
  const [periods,       setPeriods]       = useState(7)
  const [method,        setMethod]        = useState<ForecastMethod>('linear')
  const [seasonalPeriod,setSeasonalPeriod]= useState(12)
  const [result,        setResult]        = useState<ForecastResult | null>(null)
  const [running,       setRunning]       = useState(false)
  const [error,         setError]         = useState('')
  const [comparing,     setComparing]     = useState(false)
  const [compareResult, setCompareResult] = useState<ForecastCompareResult | null>(null)
  const [compareError,  setCompareError]  = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const [aiResult,  setAiResult]  = useState<ForecastInterpretResult | null>(null)
  const [aiError,   setAiError]   = useState('')
  const [showCode,  setShowCode]  = useState(false)
  const [fcScale,   setFcScale]   = useState<YScale>('auto')
  const [grain, setGrain] = useState<string>('auto')
  const [agg, setAgg] = useState<string>('sum')
  const FC_GRAINS = ['auto', 'raw', 'day', 'week', 'month', 'quarter', 'year'] as const
  const FC_AGGS = ['sum', 'mean', 'count', 'n_unique', 'min', 'max'] as const

  async function handleAiExplain() {
    if (!result) return
    setAiLoading(true); setAiError(''); setAiResult(null)
    try {
      setAiResult(await interpretForecast({
        method: result.method,
        date_col: dateCol,
        value_col: valueCol,
        periods,
        result: result as unknown as object,
        filename: dataset.filename,
      }))
    } catch (e: unknown) {
      setAiError(
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? MSG.aiExplainFailed
      )
    } finally { setAiLoading(false) }
  }

  async function handleCompare() {
    setComparing(true); setCompareError(''); setCompareResult(null)
    const methods = ['linear', 'moving_average', 'ets', 'sarimax', 'supervised']
    try {
      setCompareResult(await compareForecast(
        dataset.file_id, dateCol, valueCol, periods, seasonalPeriod, methods
      ))
    } catch (e: unknown) {
      setCompareError(
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? MSG.compareFailed
      )
    } finally { setComparing(false) }
  }

  async function runForecastWith(m: string) {
    setRunning(true); setError(''); setResult(null)
    try {
      setResult(await runForecast(
        dataset.file_id, dateCol, valueCol, periods, m,
        seasonalPeriod, grain, agg,
      ))
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? MSG.forecastFailed)
    } finally { setRunning(false) }
  }

  function handleRun() { void runForecastWith(method) }

  function handleUseRecommended(nm: string) {
    setMethod(nm as ForecastMethod)
    void runForecastWith(nm)
  }

  const meta = METHODS.find(m => m.value === method)!

  const histPoints = result?.history?.map(h => ({
    date:      h.date.slice(5),
    hist:      h.value,
    isAnomaly: h.is_anomaly,
    zScore:    h.z_score,
    value:     undefined as number | undefined,
    lower:     undefined as number | undefined,
    upper:     undefined as number | undefined,
    range:     undefined as [number, number] | undefined,
  })) ?? []

  const fcastPoints = result?.forecast.map(f => ({
    date:      f.date.slice(5),
    hist:      undefined as number | undefined,
    isAnomaly: false,
    zScore:    0,
    value:     f.value,
    lower:     f.lower,
    upper:     f.upper,
    range:     [f.lower, f.upper] as [number, number],
  })) ?? []

  const chartData = [...histPoints, ...fcastPoints]
  const separatorDate = histPoints.length > 0 ? histPoints[histPoints.length - 1].date : undefined

  const fcMaxAbs = useMemo(() => {
    if (!result) return 0
    const hist = (result.history ?? []).map(h => Math.abs(h.value))
    const fc = (result.forecast ?? []).map(p => Math.abs(p.value))
    return Math.max(0, ...hist, ...fc)
  }, [result])

  // Extra result fields beyond the standard ones
  const extraFields = result
    ? Object.entries(result as unknown as Record<string, unknown>).filter(
        ([k]) => !['method','slope','intercept','forecast','history',
                   'code','suitable','reasons','recommended_method','grain'].includes(k)
      )
    : []

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <DataQualityBanner quality={quality} qualityError={qualityError} />
      <div className="flex flex-col gap-4 p-4 flex-1 overflow-auto">
      {/* Controls */}
      <div className="flex gap-3 flex-wrap items-end">
        <div>
          <label className="block text-[10px] text-gray-600 mb-1">Method</label>
          <select className="input-base text-xs" value={method} onChange={e => setMethod(e.target.value as ForecastMethod)}>
            {['Statistical', 'Statistical (Seasonal)', 'Machine Learning'].map(g => (
              <optgroup key={g} label={g}>
                {METHODS.filter(m => m.group === g).map(m => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-[10px] text-gray-600 mb-1">Date column</label>
          <select className="input-base text-xs" value={dateCol} onChange={e => setDateCol(e.target.value)}>
            {cols.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-[10px] text-gray-600 mb-1">Value column</label>
          <select className="input-base text-xs" value={valueCol} onChange={e => setValueCol(e.target.value)}>
            {cols.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-[10px] text-gray-600 mb-1">Periods</label>
          <input type="number" min={1} max={90} className="input-base text-xs w-16"
            value={periods} onChange={e => setPeriods(Number(e.target.value))} />
        </div>
        <div>
          <label className="block text-[10px] text-gray-600 mb-1">Grain</label>
          <select className="input-base text-xs" value={grain} onChange={e => setGrain(e.target.value)}>
            {FC_GRAINS.map(g => <option key={g} value={g}>{g}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-[10px] text-gray-600 mb-1">Agg</label>
          <select className="input-base text-xs" value={agg} onChange={e => setAgg(e.target.value)}>
            {FC_AGGS.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>
        {meta.needsSeasonal && (
          <div>
            <label className="block text-[10px] text-gray-600 mb-1">Seasonal period</label>
            <div className="flex gap-1 items-center">
              <input type="number" min={2} max={365} className="input-base text-xs w-16"
                value={seasonalPeriod} onChange={e => setSeasonalPeriod(Number(e.target.value))} />
              <div className="flex gap-1">
                {SEASONAL_PRESETS.map(p => (
                  <button key={p.value} onClick={() => setSeasonalPeriod(p.value)}
                    className={`px-1.5 py-1 rounded text-[10px] border transition-all ${
                      seasonalPeriod === p.value
                        ? 'bg-analytics/10 text-analytics border-analytics/30'
                        : 'text-gray-600 border-transparent hover:text-gray-400'
                    }`}>
                    {p.value}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
        <button onClick={handleRun} disabled={running}
          className="btn-primary flex items-center gap-1.5 text-xs disabled:opacity-50">
          <TrendingUp size={12} /> {running ? 'Running…' : 'Forecast'}
        </button>
      </div>

      {/* Hint card */}
      <div className="bg-white/3 border border-white/5 rounded-lg px-3 py-2.5 text-[11px] flex flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-600 bg-white/5 px-1.5 py-0.5 rounded">{meta.group}</span>
          <span className="text-white font-medium">{meta.label}</span>
        </div>
        <p className="text-gray-300">{meta.what}</p>
        <p className="text-gray-500"><span className="text-gray-600">Khi nào dùng:</span> {meta.when}</p>
        <p className="text-gray-500"><span className="text-gray-600">Yêu cầu:</span> {meta.requires}</p>
        <p className="text-gray-500"><span className="text-gray-600">Kết quả:</span> {meta.output}</p>
      </div>

      {error && <p className="text-danger text-xs">{error}</p>}

      {result && result.suitable === false && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 space-y-3">
          <div className="flex items-center gap-2 text-amber-300 font-medium">
            <AlertTriangle size={16} />
            Dữ liệu chưa phù hợp với phương pháp này
          </div>
          <ul className="list-disc list-inside text-sm text-amber-100/90 space-y-1">
            {(result.reasons ?? []).map((r, i) => <li key={i}>{r}</li>)}
          </ul>
          {result.recommended_method && (
            <button
              onClick={() => handleUseRecommended(result.recommended_method!)}
              className="inline-flex items-center gap-1.5 rounded-md bg-amber-500/20 hover:bg-amber-500/30 px-3 py-1.5 text-sm text-amber-100 transition-colors"
            >
              <Sparkles size={14} />
              Dùng {result.recommended_method} thay thế
            </button>
          )}
          {result.code && <CodePanel code={result.code} filename="forecast_pipeline.py" />}
        </div>
      )}

      {result && result.suitable !== false && (
        <>
          <div className="flex justify-end">
            <div className="flex gap-1">
              {(['auto', 'K', 'M', 'B', '%'] as YScale[]).map(s => (
                <button
                  key={s}
                  onClick={() => setFcScale(s)}
                  className={`px-2 py-0.5 text-xs rounded transition-colors ${
                    fcScale === s ? 'bg-blue-500/30 text-blue-200' : 'text-gray-400 hover:text-gray-200'
                  }`}
                >{s}</button>
              ))}
            </div>
          </div>
          <div className="bg-secondary border border-white/5 rounded-lg p-4" style={{ height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 10 }} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={(v) => fmtY(v, fcScale, fcMaxAbs)} width={65} />
                <Tooltip
                  formatter={(value, name) => {
                    const labels: Record<string, string> = {
                      hist: 'Lịch sử', value: 'Dự báo',
                      lower: 'CI thấp', upper: 'CI cao',
                    }
                    return [fmtFull(value as number), labels[String(name)] ?? name]
                  }}
                  contentStyle={{ background: '#161b22', border: '1px solid rgba(255,255,255,0.1)', fontSize: 12 }}
                />
                <Area
                  type="monotone" dataKey="range"
                  fill="#60a5fa" fillOpacity={0.12} stroke="none"
                />
                <Line
                  type="monotone" dataKey="hist"
                  stroke="#60a5fa" strokeWidth={2}
                  dot={(props: unknown) => {
                    const { cx, cy, payload } = props as { cx: number; cy: number; payload: { isAnomaly: boolean } }
                    if (payload.isAnomaly) {
                      return <circle key={`a-${cx}-${cy}`} cx={cx} cy={cy} r={5} fill="#ef4444" stroke="#ef4444" strokeWidth={1} />
                    }
                    return <circle key={`h-${cx}-${cy}`} cx={cx} cy={cy} r={2} fill="#60a5fa" />
                  }}
                  connectNulls={false}
                />
                <Line
                  type="monotone" dataKey="value"
                  stroke="#60a5fa" strokeWidth={2}
                  strokeDasharray="5 3"
                  dot={{ r: 3, fill: '#60a5fa' }}
                  connectNulls={false}
                />
                {separatorDate && (
                  <ReferenceLine
                    x={separatorDate}
                    stroke="rgba(255,255,255,0.2)"
                    strokeDasharray="4 2"
                    label={{ value: 'Dự báo →', position: 'top', fill: '#6b7280', fontSize: 9 }}
                  />
                )}
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Extra metrics (AIC, R², etc.) */}
          {extraFields.length > 0 && (
            <div className="flex gap-4 flex-wrap">
              {extraFields.map(([k, v]) => (
                <div key={k} className="bg-white/3 border border-white/5 rounded px-3 py-1.5">
                  <p className="text-[10px] text-gray-600 uppercase tracking-wider">{k.replace(/_/g, ' ')}</p>
                  <p className="text-sm font-semibold text-white">{typeof v === 'number' ? fmtFull(v) : String(v)}</p>
                </div>
              ))}
            </div>
          )}

          {/* AI Explanation */}
          <div>
            <button
              onClick={handleAiExplain}
              disabled={aiLoading}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded border border-white/10 text-gray-400 hover:text-white hover:border-white/20 transition-colors disabled:opacity-40"
            >
              <Sparkles size={12} />
              {aiLoading ? 'Đang phân tích...' : 'Giải thích AI'}
            </button>

            {aiError && <p className="text-danger text-xs mt-2">{aiError}</p>}

            {aiResult && (
              <div className="mt-3 bg-white/3 border border-white/5 rounded-lg p-4 flex flex-col gap-3 text-[11px]">
                <div>
                  <p className="text-[10px] text-analytics uppercase tracking-wider mb-1">Tóm tắt</p>
                  <p className="text-gray-300 leading-relaxed">{aiResult.summary}</p>
                </div>
                <div>
                  <p className="text-[10px] text-analytics uppercase tracking-wider mb-1">Xu hướng</p>
                  <p className="text-gray-300 leading-relaxed">{aiResult.trend}</p>
                </div>
                <div>
                  <p className="text-[10px] text-analytics uppercase tracking-wider mb-1">Đề xuất</p>
                  <p className="text-gray-300 leading-relaxed">{aiResult.actions}</p>
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between">
            <p className="text-gray-600 text-[10px]">
              {result.method} · shaded = 95% CI
            </p>
            <div className="flex items-center gap-3">
              <button
                onClick={() => downloadCsv(result, valueCol)}
                className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors"
              >
                <Download size={12} /> Export CSV
              </button>
              <button
                onClick={() => setShowCode(o => !o)}
                className={`flex items-center gap-1.5 text-xs transition-colors ${showCode ? 'text-analytics' : 'text-gray-500 hover:text-gray-300'}`}
              >
                <Code2 size={12} /> {showCode ? 'Hide Code' : 'Show Code'}
              </button>
            </div>
          </div>

          {showCode && (
            <CodePanel
              code={result?.code ?? ''}
              filename="forecast.py"
            />
          )}
        </>
      )}
      {/* Model comparison */}
      <div className="flex gap-2 items-center">
        <button
          onClick={handleCompare} disabled={comparing}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors disabled:opacity-40"
        >
          <BarChart2 size={12} /> {comparing ? 'Đang so sánh...' : 'So sánh Model'}
        </button>
      </div>

      {compareError && <p className="text-danger text-xs">{compareError}</p>}

      {compareResult && (
        <div className="bg-secondary border border-white/5 rounded-lg overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/5">
                <th className="text-left px-3 py-2 text-gray-600 font-normal">Model</th>
                <th className="text-right px-3 py-2 text-gray-600 font-normal">MAPE</th>
                <th className="text-right px-3 py-2 text-gray-600 font-normal">RMSE</th>
                <th className="text-right px-3 py-2 text-gray-600 font-normal">AIC</th>
                <th className="text-center px-3 py-2 text-gray-600 font-normal">Status</th>
              </tr>
            </thead>
            <tbody>
              {compareResult.results.map((r) => (
                <tr
                  key={r.method}
                  className={`border-b border-white/5 last:border-0 transition-colors ${
                    r.method === compareResult.best
                      ? 'bg-analytics/10 border-l-2 border-l-analytics'
                      : 'hover:bg-white/2'
                  }`}
                >
                  <td className="px-3 py-2 text-white">
                    {r.method === compareResult.best && <Star size={12} className="inline mr-1" />}
                    {r.label}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-300">
                    {r.mape != null ? `${r.mape.toFixed(1)}%` : '—'}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-300">
                    {r.rmse != null ? fmtFull(r.rmse) : '—'}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-300">
                    {r.aic != null ? r.aic.toFixed(1) : '—'}
                  </td>
                  <td className="px-3 py-2 text-center">
                    {r.status === 'ok'
                      ? <Check size={14} className="inline text-green-400" />
                      : <span title={r.error}><X size={14} className="inline text-red-400" /></span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="px-3 py-1.5 text-[10px] text-gray-600">
            Cross-validation 80/20 · thấp hơn = tốt hơn · phương pháp tốt nhất được đánh dấu sao
          </p>
        </div>
      )}
      </div>
    </div>
  )
}
