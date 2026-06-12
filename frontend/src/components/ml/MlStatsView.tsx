import { useState } from 'react'
import { FlaskConical, Code2, Sparkles, ChevronDown, ChevronUp, Hash, Lightbulb, Target } from 'lucide-react'
import CodePanel from './CodePanel'
import ZScoreResult from './ZScoreResult'
import BoxPlotResult from './BoxPlotResult'
import type { DatasetInfo, StatsResult, QualityResult, ZScoreData, BoxPlotData } from '../../types'
import { runStats, interpretStats, runBoxPlot } from '../../api/ml'
import type { StatsInterpretation } from '../../api/ml'
import DataQualityBanner from './DataQualityBanner'
import { MSG } from '../../messages'

interface Props { dataset: DatasetInfo; quality: QualityResult | null; qualityError?: boolean }

type TestType = 'describe' | 'correlation' | 'ttest' | 'distribution'
  | 'anova' | 'chi2' | 'bootstrap' | 'mannwhitney' | 'zscore' | 'boxplot'

const TESTS: { value: TestType; label: string; needsColB: boolean; colBHint?: string }[] = [
  { value: 'describe',     label: 'Describe',        needsColB: false },
  { value: 'bootstrap',    label: 'Bootstrap CI',     needsColB: false },
  { value: 'zscore',       label: 'Z-Score',          needsColB: false },
  { value: 'boxplot',      label: 'Box Plot',         needsColB: false },
  { value: 'distribution', label: 'Distribution',     needsColB: false },
  { value: 'correlation',  label: 'Correlation',      needsColB: true,  colBHint: 'numeric' },
  { value: 'ttest',        label: 'T-Test',           needsColB: true,  colBHint: 'numeric' },
  { value: 'mannwhitney',  label: 'Mann-Whitney U',   needsColB: true,  colBHint: 'numeric' },
  { value: 'anova',        label: 'ANOVA',            needsColB: true,  colBHint: 'phân nhóm' },
  { value: 'chi2',         label: 'Chi-Square',       needsColB: true,  colBHint: 'categorical' },
]

const HINTS: Record<TestType, { what: string; when: string; colA: string; colB?: string }> = {
  describe:     { what: 'Tóm tắt thống kê cơ bản: mean, std, min, max, phân vị 25/50/75.',
                  when: 'Dùng đầu tiên khi nhận dataset mới để hiểu nhanh phân phối.',
                  colA: 'Cột số bất kỳ — VD: doanh thu, số ngày, số lần mua.' },
  bootstrap:    { what: 'Ước tính khoảng tin cậy 95% cho mean bằng cách lấy mẫu lặp lại 1000 lần.',
                  when: 'Dùng khi mẫu nhỏ hoặc không chắc phân phối có chuẩn không.',
                  colA: 'Cột số — VD: transaction_interval, revenue.' },
  distribution: { what: 'Vẽ histogram xem giá trị tập trung ở đâu, có lệch trái/phải không.',
                  when: 'Dùng trước khi chọn test thống kê — phân phối lệch thì không dùng T-Test.',
                  colA: 'Cột số — VD: giá trị đơn hàng, số ngày giữa 2 lần mua.' },
  correlation:  { what: 'Đo tương quan tuyến tính giữa 2 cột số (r: -1 đến 1). |r| > 0.7 = mạnh.',
                  when: 'Dùng khi hỏi "A tăng thì B có tăng theo không?"',
                  colA: 'Cột số thứ nhất — VD: số lần mua.',
                  colB: 'Cột số thứ hai — VD: tổng doanh thu.' },
  ttest:        { what: 'Kiểm định mean của 2 nhóm có khác nhau có ý nghĩa không. p < 0.05 = có.',
                  when: 'Dùng khi so sánh 2 nhóm — VD: khách mới vs khách cũ. Cần phân phối gần chuẩn.',
                  colA: 'Cột số nhóm 1 — VD: doanh thu của nhóm A.',
                  colB: 'Cột số nhóm 2 — VD: doanh thu của nhóm B.' },
  mannwhitney:  { what: 'Giống T-Test nhưng không cần phân phối chuẩn — bền với outlier.',
                  when: 'Dùng thay T-Test khi distribution bị lệch hoặc có nhiều giá trị ngoại lai.',
                  colA: 'Cột số nhóm 1.',
                  colB: 'Cột số nhóm 2.' },
  anova:        { what: 'So sánh mean của cột A trên nhiều nhóm trong cột B. p < 0.05 = ít nhất 1 nhóm khác.',
                  when: 'Dùng khi có ≥ 3 nhóm cần so sánh — VD: doanh thu theo brand, tier, region.',
                  colA: 'Cột số cần so sánh — VD: transaction_interval, revenue.',
                  colB: 'Cột phân nhóm (text/category) — VD: Master_Brand__c, Customer_Tier.' },
  chi2:         { what: 'Kiểm định 2 cột phân loại có liên quan đến nhau không. p < 0.05 = có liên quan.',
                  when: 'Dùng cho câu hỏi "Brand X có xu hướng chọn kênh Y không?"',
                  colA: 'Cột categorical 1 — VD: Brand, Tier.',
                  colB: 'Cột categorical 2 — VD: Channel, Region.' },
  zscore:       { what: 'Tính z-score cho mỗi giá trị: (x − mean) / std. Phát hiện giá trị bất thường và hiện phân phối chuẩn hoá.',
                  when: 'Dùng khi muốn biết giá trị nào bất thường, hoặc trước khi đưa dữ liệu vào model ML cần chuẩn hoá.',
                  colA: 'Cột số bất kỳ — VD: doanh thu, số ngày, transaction_interval.' },
  boxplot:      { what: 'Vẽ box plot (min/Q1/median/Q3/max) cho 1 cột số, hoặc so sánh phân phối nhiều nhóm khi chọn cột B. Tự phát hiện outlier (vượt 1.5×IQR).',
                  when: 'Dùng để xem nhanh độ rải, độ skew, outlier; hoặc so sánh phân phối giữa các nhóm trước khi chạy ANOVA / Mann-Whitney.',
                  colA: 'Cột số bất kỳ — VD: doanh thu, transaction_interval.',
                  colB: '(Optional) Cột phân nhóm để so sánh — VD: Brand, Tier, Region.' },
}

function isNumeric(dtype: string) {
  return /Float|Int|UInt/i.test(dtype)
}

export default function MlStatsView({ dataset, quality, qualityError }: Props) {
  const allCols     = dataset.columns.map(c => c.name)
  const numericCols = dataset.columns.filter(c => isNumeric(c.dtype)).map(c => c.name)

  const [test,    setTest]    = useState<TestType>('describe')
  const [colA,    setColA]    = useState(numericCols[0] ?? allCols[0] ?? '')
  const [colB,    setColB]    = useState(numericCols[1] ?? numericCols[0] ?? allCols[1] ?? '')
  const [result,         setResult]         = useState<StatsResult | null>(null)
  const [running,        setRunning]        = useState(false)
  const [error,          setError]          = useState('')
  const [interpretation, setInterpretation] = useState<StatsInterpretation | null>(null)
  const [interpreting,   setInterpreting]   = useState(false)
  const [aiError,        setAiError]        = useState('')
  const [aiOpen,         setAiOpen]         = useState(true)
  const [showCode,       setShowCode]       = useState(false)
  const [useGroupBy,     setUseGroupBy]     = useState(false)
  const [maxGroups,      setMaxGroups]      = useState(10)

  const testMeta    = TESTS.find(t => t.value === test)!
  const needsColB   = testMeta.needsColB
  const showColB    = needsColB || (test === 'boxplot' && useGroupBy)
  // ANOVA, Chi2, and Box Plot group column can be any column; numeric tests need numeric col B
  const colBOptions = (test === 'anova' || test === 'chi2' || test === 'boxplot') ? allCols : numericCols

  // Switching the test must clear the previous result. Each test renders a
  // dedicated component (ZScoreResult reads .rows, BoxPlotResult reads .groups);
  // leaving a stale, incompatible result mounted crashes the next render — this
  // was the "Box Plot works but switching to Z-Score errors" bug.
  function handleTestChange(next: TestType) {
    setTest(next)
    setResult(null)
    setError('')
    setInterpretation(null)
    setAiError('')
  }

  async function handleRun(overrideMaxGroups?: number) {
    setRunning(true); setError(''); setResult(null)
    setInterpretation(null); setAiError('')
    try {
      if (test === 'boxplot') {
        const r = await runBoxPlot(
          dataset.file_id, colA,
          useGroupBy ? colB : undefined,
          overrideMaxGroups ?? maxGroups,
        )
        setResult(r as unknown as StatsResult)
      } else {
        setResult(await runStats(dataset.file_id, test, colA, needsColB ? colB : undefined))
      }
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? MSG.statsFailed)
    } finally { setRunning(false) }
  }

  async function handleMaxGroupsChange(newMax: number) {
    setMaxGroups(newMax)
    await handleRun(newMax)
  }

  async function handleInterpret() {
    if (!result) return
    setInterpreting(true); setAiError(''); setAiOpen(true)
    try {
      const r = await interpretStats(test, colA, needsColB ? colB : undefined, result as Record<string, unknown>, dataset.filename)
      setInterpretation(r)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setAiError(detail ?? MSG.aiInterpretFailed)
    } finally { setInterpreting(false) }
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <DataQualityBanner quality={quality} qualityError={qualityError} />
      <div className="flex flex-col gap-4 p-4 flex-1 overflow-auto">
      <div className="flex gap-3 flex-wrap items-end">
        <div>
          <label className="block text-[10px] text-gray-600 mb-1">Test</label>
          <select className="input-base text-xs" value={test} onChange={e => handleTestChange(e.target.value as TestType)}>
            {TESTS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-[10px] text-gray-600 mb-1">
            Column A (numeric{numericCols.length === 0 ? ' — none detected' : ''})
          </label>
          <select className="input-base text-xs" value={colA} onChange={e => setColA(e.target.value)}>
            {(test === 'chi2' ? allCols : numericCols).map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        {test === 'boxplot' && (
          <div className="flex items-end pb-1.5">
            <label className="flex items-center gap-1.5 text-[11px] text-gray-400 cursor-pointer">
              <input
                type="checkbox"
                checked={useGroupBy}
                onChange={e => setUseGroupBy(e.target.checked)}
                className="accent-analytics"
              />
              So sánh theo nhóm
            </label>
          </div>
        )}
        {showColB && (
          <div>
            <label className="block text-[10px] text-gray-600 mb-1">
              Column B{testMeta.colBHint ? ` (${testMeta.colBHint})` : ' (phân nhóm)'}
            </label>
            <select className="input-base text-xs" value={colB} onChange={e => setColB(e.target.value)}>
              {colBOptions.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        )}
        <button
          onClick={() => handleRun()}
          disabled={running}
          className="btn-primary flex items-center gap-1.5 text-xs disabled:opacity-50"
        >
          <FlaskConical size={12} /> {running ? 'Running…' : 'Run'}
        </button>
      </div>

      {/* Hint card */}
      {(() => {
        const h = HINTS[test]
        return (
          <div className="bg-white/3 border border-white/5 rounded-lg px-3 py-2.5 text-[11px] flex flex-col gap-1">
            <p className="text-gray-300">{h.what}</p>
            <p className="text-gray-500">Khi nào dùng: {h.when}</p>
            <div className="flex flex-wrap gap-x-4 gap-y-0.5 mt-0.5">
              <span className="text-gray-600">Col A → <span className="text-gray-400">{h.colA}</span></span>
              {h.colB && <span className="text-gray-600">Col B → <span className="text-gray-400">{h.colB}</span></span>}
            </div>
          </div>
        )
      })()}

      {error && <p className="text-danger text-xs">{error}</p>}

      {result && (
        <>
          {/* Results — routed by test type */}
          {test === 'zscore' ? (
            'rows' in result ? (
              <ZScoreResult
                data={result as unknown as ZScoreData}
                colA={colA}
                fileId={dataset.file_id}
              />
            ) : null
          ) : test === 'boxplot' ? (
            'groups' in result ? (
              <BoxPlotResult
                data={result as unknown as BoxPlotData}
                colA={colA}
                colB={useGroupBy ? colB : undefined}
                fileId={dataset.file_id}
                maxGroups={maxGroups}
                onMaxGroupsChange={handleMaxGroupsChange}
              />
            ) : null
          ) : (
            <div className="bg-secondary border border-white/5 rounded-lg p-4">
              <div className="grid grid-cols-2 gap-3">
                {Object.entries(result).filter(([k]) => k !== 'code').map(([k, v]) => (
                  <div key={k}>
                    <p className="text-[10px] text-gray-600 uppercase tracking-wider">{k}</p>
                    <p className={`text-sm font-semibold ${typeof v === 'string' && v.includes('significant') ? 'text-work' : 'text-white'}`}>
                      {typeof v === 'number' ? v.toLocaleString('vi-VN', { maximumFractionDigits: 4 }) : String(v)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Toolbar */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowCode(o => !o)}
              className={`flex items-center gap-1.5 text-xs transition-colors ${showCode ? 'text-analytics' : 'text-gray-500 hover:text-gray-300'}`}
            >
              <Code2 size={12} /> {showCode ? 'Hide Code' : 'Show Code'}
            </button>
            {test !== 'zscore' && test !== 'boxplot' && (
            <button
              onClick={handleInterpret}
              disabled={interpreting}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border
                         bg-learn/10 text-learn border-learn/30 hover:border-learn/60
                         disabled:opacity-40 transition-all"
            >
              <Sparkles size={12} className={interpreting ? 'animate-pulse' : ''} />
              {interpreting ? 'Đang phân tích...' : interpretation ? 'Phân tích lại' : 'Giải thích AI'}
            </button>
            )}
          </div>

          {/* Show Code panel */}
          {showCode && (
            <CodePanel
              code={String(result.code ?? '')}
              filename="stats_analysis.py"
            />
          )}

          {/* AI Interpretation */}
          {(interpretation || aiError) && (
            <div className="border border-learn/20 rounded-xl overflow-hidden">
              {/* Header */}
              <button
                onClick={() => setAiOpen(o => !o)}
                className="w-full flex items-center justify-between px-4 py-2.5
                           bg-learn/5 border-b border-learn/10 text-left"
              >
                <span className="text-[11px] font-semibold text-learn/80 uppercase tracking-widest flex items-center gap-1.5">
                  <Sparkles size={11} /> Phân tích từ Senior DA
                </span>
                {aiOpen ? <ChevronUp size={13} className="text-gray-500" /> : <ChevronDown size={13} className="text-gray-500" />}
              </button>

              {aiOpen && (
                <div className="p-4 space-y-4 bg-learn/3">
                  {aiError && <p className="text-danger text-xs">{aiError}</p>}

                  {interpretation && (
                    <>
                      {/* Numbers explained */}
                      <div>
                        <p className="text-[10px] uppercase tracking-widest text-gray-500 mb-1.5 flex items-center gap-1">
                          <Hash size={14} /> Ý nghĩa các con số
                        </p>
                        <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap">
                          {interpretation.numbers}
                        </p>
                      </div>

                      <hr className="border-white/5" />

                      {/* Insights */}
                      <div>
                        <p className="text-[10px] uppercase tracking-widest text-gray-500 mb-1.5 flex items-center gap-1">
                          <Lightbulb size={14} /> Insights
                        </p>
                        <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap">
                          {interpretation.insights}
                        </p>
                      </div>

                      <hr className="border-white/5" />

                      {/* Actions */}
                      <div>
                        <p className="text-[10px] uppercase tracking-widest text-gray-500 mb-1.5 flex items-center gap-1">
                          <Target size={14} /> Đề xuất hành động
                        </p>
                        <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap">
                          {interpretation.actions}
                        </p>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
      </div>
    </div>
  )
}
