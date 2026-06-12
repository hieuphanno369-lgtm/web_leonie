import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Database, ChevronRight, ChevronDown, Play, Clock,
  Trash2, Upload, Copy, Check, BookOpen,
  Lightbulb, CheckCircle2, AlertCircle, Tag, FlaskConical,
} from 'lucide-react'
import {
  fetchTables, runSql, deleteDataset, seedVinaBrew, checkExercise,
  type TableInfo, type SqlResult,
} from '../../api/sql'
import { uploadFile } from '../../api/ml'
import { VINA_BREW_EXERCISES } from '../../data/vina_brew_exercises'
import { SCHEMA_META } from '../../data/vina_brew_schema_meta'
import MetricsDictPanel from '../../components/sql/MetricsDictPanel'
import QuerySuggestPanel from '../../components/sql/QuerySuggestPanel'
import SqlEditor from '../../components/sql/SqlEditor'
import { MSG } from '../../messages'

// ── LocalStorage keys ────────────────────────────────────────────────────────
const HISTORY_KEY  = 'sql_sandbox_history'
const PROGRESS_KEY = 'sql_sandbox_progress'
const MAX_HISTORY  = 20

interface HistoryEntry { sql: string; ts: number; rows: number; ms: number }
type Progress = Record<string, 'passed' | 'attempted'>

function loadHistory(): HistoryEntry[] {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) ?? '[]') } catch { return [] }
}
function saveHistory(h: HistoryEntry[]) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(h.slice(0, MAX_HISTORY)))
}
function loadProgress(): Progress {
  try { return JSON.parse(localStorage.getItem(PROGRESS_KEY) ?? '{}') } catch { return {} }
}
function saveProgress(p: Progress) {
  localStorage.setItem(PROGRESS_KEY, JSON.stringify(p))
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function isNumericCol(dtype: string) { return /Float|Int|UInt|DOUBLE|BIGINT|DECIMAL/i.test(dtype) }

function fmtNum(v: unknown): string {
  const n = Number(v)
  if (isNaN(n)) return String(v)
  return n.toLocaleString('vi-VN', { maximumFractionDigits: 4 })
}

// Parse DuckDB error string into type + Vietnamese message
function parseError(raw: string): { type: string; msg: string } {
  if (/Parser Error/i.test(raw)) {
    const detail = raw.replace(/^.*Parser Error[:\s]*/i, '').trim()
    return { type: 'syntax', msg: `Lỗi cú pháp SQL: ${detail}` }
  }
  if (/Binder Error/i.test(raw)) {
    const colMatch = raw.match(/Referenced column "([^"]+)" not found/i)
      ?? raw.match(/column "([^"]+)" not found/i)
    if (colMatch) {
      return { type: 'field', msg: `Không tìm thấy column "${colMatch[1]}". Kiểm tra tên column trong Schema Browser bên trái.` }
    }
    const tblMatch = raw.match(/Table with name "?([^"\s]+)"? does not exist/i)
      ?? raw.match(/did not find table[: ]+"?([^"\s]+)"?/i)
    if (tblMatch) {
      return { type: 'table', msg: `Table "${tblMatch[1]}" không tồn tại. Xem danh sách table trong Schema Browser.` }
    }
    return { type: 'field', msg: `Lỗi tham chiếu: ${raw.replace(/^.*Binder Error[:\s]*/i,'').trim()}` }
  }
  if (/Table.*does not exist|did not find table/i.test(raw)) {
    const m = raw.match(/"([^"]+)"/)
    return { type: 'table', msg: `Table "${m?.[1] ?? 'unknown'}" không tồn tại. Xem Schema Browser.` }
  }
  return { type: 'other', msg: raw }
}

const DIFF_CLS: Record<string, string> = {
  easy:   'bg-green-900/60 text-green-400',
  medium: 'bg-yellow-900/60 text-yellow-400',
  hard:   'bg-red-900/60 text-red-400',
}

// ── ExercisesPanel ───────────────────────────────────────────────────────────
function ExercisesPanel({
  onInject,
  selectedId,
  onSelect,
  progress,
  onCheck,
}: {
  onInject:  (sql: string) => void
  selectedId: string | null
  onSelect:  (id: string | null) => void
  progress:  Progress
  onCheck:   (exerciseId: string, expectedColumns: string[]) => Promise<{ passed: boolean; error?: string }>
}) {
  const [open,        setOpen]        = useState(false)
  const [hintTier,    setHintTier]    = useState(0)
  const [checkResult, setCheckResult] = useState<{ passed: boolean; error?: string } | null>(null)

  const ex = selectedId ? VINA_BREW_EXERCISES.find(e => e.id === selectedId) ?? null : null

  const groups = {
    easy:   VINA_BREW_EXERCISES.filter(e => e.difficulty === 'easy'),
    medium: VINA_BREW_EXERCISES.filter(e => e.difficulty === 'medium'),
    hard:   VINA_BREW_EXERCISES.filter(e => e.difficulty === 'hard'),
  } as const

  const totalPassed = Object.values(progress).filter(v => v === 'passed').length

  function selectEx(id: string) {
    onSelect(id); setHintTier(0); setCheckResult(null)
  }
  function back() {
    onSelect(null); setHintTier(0); setCheckResult(null)
  }

  return (
    <div className="border-t border-white/5 flex-shrink-0">
      <button
        onClick={() => { setOpen(o => !o); if (open) back() }}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/3 transition-colors text-left"
      >
        <BookOpen size={11} className="text-analytics flex-shrink-0" />
        <span className="text-[11px] font-semibold text-gray-300 flex-1">Exercises</span>
        <span className="text-[9px] text-green-400 mr-1">{totalPassed}/{VINA_BREW_EXERCISES.length}</span>
        {open
          ? <ChevronDown  size={11} className="text-gray-600" />
          : <ChevronRight size={11} className="text-gray-600" />}
      </button>

      {open && (
        ex ? (
          /* ── Exercise detail ── */
          <div className="px-3 pb-3 space-y-2">
            <button onClick={back}
              className="text-[10px] text-gray-500 hover:text-gray-300 flex items-center gap-1">
              ← back
            </button>

            <div className="flex items-center gap-1.5 flex-wrap">
              <span className={`text-[9px] px-1.5 rounded ${DIFF_CLS[ex.difficulty]}`}>{ex.difficulty}</span>
              <span className="text-[9px] text-gray-600">{ex.category}</span>
              {progress[ex.id] === 'passed' && (
                <span className="text-[9px] text-green-400 flex items-center gap-0.5">
                  <CheckCircle2 size={9} /> Hoàn thành
                </span>
              )}
            </div>

            <p className="text-[11px] font-semibold text-white">{ex.title}</p>
            <p className="text-[10px] text-gray-400 leading-relaxed">{ex.description}</p>
            <p className="text-[10px] text-blue-300/60 leading-relaxed italic">{ex.businessContext}</p>
            <p className="text-[9px] text-gray-600">Columns: {ex.expectedColumns.join(', ')}</p>

            <button
              onClick={() => onInject(ex.starterQuery)}
              className="w-full text-[10px] btn-primary py-1 rounded text-center"
            >
              ↳ Inject starter SQL
            </button>

            {/* Check answer */}
            <button
              onClick={async () => {
                const res = await onCheck(ex.id, ex.expectedColumns)
                setCheckResult(res)
              }}
              className="w-full text-[10px] py-1 rounded text-center border border-analytics/30 text-analytics hover:bg-analytics/10 transition-colors"
            >
              ✓ Check Answer
            </button>

            {/* Check result feedback */}
            {checkResult && (
              <div className={`flex items-start gap-1.5 px-2 py-1.5 rounded text-[10px] ${
                checkResult.passed
                  ? 'bg-green-950/40 text-green-400'
                  : 'bg-red-950/40 text-red-400'
              }`}>
                {checkResult.passed
                  ? <CheckCircle2 size={11} className="flex-shrink-0 mt-0.5" />
                  : <AlertCircle  size={11} className="flex-shrink-0 mt-0.5" />}
                <span>{checkResult.passed
                  ? 'Chính xác! Các cột khớp.'
                  : checkResult.error ?? 'Các cột chưa khớp — thử lại nhé.'
                }</span>
              </div>
            )}

            {/* 3-tier hints */}
            {hintTier >= 1 && (
              <div className="bg-white/3 rounded px-2 py-1.5">
                <p className="text-[9px] text-yellow-500 mb-0.5">Hint 1 — Hướng tiếp cận</p>
                <p className="text-[10px] text-gray-400 leading-relaxed whitespace-pre-wrap">{ex.hints[0]}</p>
              </div>
            )}
            {hintTier >= 2 && (
              <div className="bg-white/3 rounded px-2 py-1.5">
                <p className="text-[9px] text-yellow-500 mb-0.5">Hint 2 — Keywords (DuckDB + T-SQL)</p>
                <pre className="text-[9px] font-mono text-yellow-300/80 whitespace-pre-wrap leading-relaxed">{ex.hints[1]}</pre>
              </div>
            )}
            {hintTier >= 3 && (
              <div className="bg-white/3 rounded px-2 py-1.5">
                <p className="text-[9px] text-green-500 mb-0.5">Hint 3 — Đáp án đầy đủ</p>
                <pre className="text-[9px] font-mono text-green-300/80 whitespace-pre-wrap leading-relaxed">{ex.hints[2]}</pre>
                <button onClick={() => onInject(ex.solutionQuery)}
                  className="text-[9px] text-gray-500 hover:text-gray-300 mt-1">
                  ↳ Load solution
                </button>
              </div>
            )}

            {hintTier < 3 && (
              <button
                onClick={() => setHintTier(t => t + 1)}
                className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-yellow-400 transition-colors"
              >
                <Lightbulb size={10} />
                {hintTier === 0 ? 'Hint 1: Hướng tiếp cận'
                  : hintTier === 1 ? 'Hint 2: Keywords'
                  : 'Hint 3: Đáp án'}
              </button>
            )}

            <p className="text-[10px] text-blue-300/50 leading-relaxed pt-1 border-t border-white/5">
              {ex.explanation}
            </p>
          </div>
        ) : (
          /* ── Exercise list ── */
          <div className="max-h-72 overflow-y-auto">
            {(['easy','medium','hard'] as const).map(diff => {
              const list   = groups[diff]
              const passed = list.filter(e => progress[e.id] === 'passed').length
              return (
                <div key={diff}>
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-white/2">
                    <span className={`text-[9px] px-1.5 rounded ${DIFF_CLS[diff]}`}>{diff}</span>
                    <span className="text-[9px] text-green-400 ml-auto">{passed}/{list.length}</span>
                  </div>
                  {list.map(e => (
                    <button key={e.id} onClick={() => selectEx(e.id)}
                      className="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/3 transition-colors text-left border-b border-white/3">
                      {progress[e.id] === 'passed'
                        ? <CheckCircle2 size={10} className="text-green-400 flex-shrink-0" />
                        : progress[e.id] === 'attempted'
                        ? <AlertCircle  size={10} className="text-yellow-600 flex-shrink-0" />
                        : <span className="w-[10px] flex-shrink-0" />}
                      <span className="text-[10px] text-gray-300 truncate flex-1">{e.title}</span>
                      <span className="text-[9px] text-gray-700 shrink-0">{e.category}</span>
                      <ChevronRight size={9} className="text-gray-700 shrink-0" />
                    </button>
                  ))}
                </div>
              )
            })}
          </div>
        )
      )}
    </div>
  )
}

// ── VINA BREW table relationships ────────────────────────────────────────────
const VINA_BREW_RELATIONS = [
  {
    from: 'fact_sales', alias: 's',
    joins: [
      { to: 'dim_date',    alias: 'd', key: 'date_key' },
      { to: 'dim_product', alias: 'p', key: 'product_id' },
      { to: 'dim_store',   alias: 'st', key: 'store_id' },
      { to: 'dim_channel', alias: 'ch', key: 'channel_id' },
    ],
  },
  {
    from: 'fact_transactions', alias: 't',
    joins: [
      { to: 'dim_date',    alias: 'd',  key: 'date_key' },
      { to: 'dim_product', alias: 'p',  key: 'product_id' },
      { to: 'dim_store',   alias: 'st', key: 'store_id' },
    ],
  },
  {
    from: 'dim_store', alias: 'st',
    joins: [
      { to: 'dim_channel', alias: 'ch', key: 'channel_id' },
    ],
  },
]

function RelationsPanel({ onInsert }: { onInsert: (s: string) => void }) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState<string | null>(null)

  function copyJoin(snippet: string, id: string) {
    navigator.clipboard.writeText(snippet)
    setCopied(id)
    setTimeout(() => setCopied(null), 1200)
  }

  return (
    <div className="border-t border-white/5 flex-shrink-0">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/3 transition-colors text-left"
      >
        {open
          ? <ChevronDown  size={11} className="text-gray-600 flex-shrink-0" />
          : <ChevronRight size={11} className="text-gray-600 flex-shrink-0" />}
        <span className="text-[11px] font-semibold text-gray-400 flex-1">Relations</span>
        <span className="text-[9px] text-gray-700">FK / JOIN</span>
      </button>

      {open && (
        <div className="pb-2 space-y-3 px-3">
          {VINA_BREW_RELATIONS.map(rel => (
            <div key={rel.from}>
              <p className="text-[10px] font-mono text-data mb-1">
                {rel.from}
                <span className="text-gray-600 font-normal"> ({rel.alias})</span>
              </p>
              {rel.joins.map(j => {
                const snippet = `JOIN ${j.to} ${j.alias} ON ${rel.alias}.${j.key} = ${j.alias}.${j.key}`
                const id = `${rel.from}-${j.to}`
                return (
                  <div
                    key={j.to}
                    className="flex items-start gap-1.5 pl-2 py-0.5 group"
                  >
                    <span className="text-[9px] text-gray-600 flex-shrink-0 mt-0.5">→</span>
                    <div className="flex-1 min-w-0">
                      <button
                        onClick={() => onInsert(snippet)}
                        className="text-left w-full"
                        title="Click to insert"
                      >
                        <span className="text-[9px] font-mono text-analytics">{j.to}</span>
                        <span className="text-[9px] text-gray-600"> ON </span>
                        <span className="text-[9px] font-mono text-yellow-400/80">{j.key}</span>
                      </button>
                      <p className="text-[8px] font-mono text-gray-700 truncate">{snippet}</p>
                    </div>
                    <button
                      onClick={() => copyJoin(snippet, id)}
                      className="opacity-0 group-hover:opacity-100 flex-shrink-0 text-gray-600 hover:text-gray-400 transition-colors"
                      title="Copy JOIN snippet"
                    >
                      {copied === id
                        ? <Check size={9} className="text-green-400" />
                        : <Copy size={9} />}
                    </button>
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── SchemaPanel ───────────────────────────────────────────────────────────────
function SchemaPanel({
  tables, loading, onInsert, onDelete, onSeed, seeding,
}: {
  tables:   TableInfo[]
  loading:  boolean
  onInsert: (s: string) => void
  onDelete: (fileId: string, name: string) => void
  onSeed:   () => void
  seeding:  boolean
}) {
  const [open, setOpen] = useState<Record<string, boolean>>({})

  function toggle(name: string) { setOpen(o => ({ ...o, [name]: !o[name] })) }

  if (loading) return <p className="text-[10px] text-gray-600 p-3">{MSG.loadingTables}</p>

  const vinaBrewTables = tables.filter(t => t.source === 'vina_brew')

  return (
    <div className="flex flex-col">
      {/* Seed VINA BREW button (shown when no VB tables yet) */}
      {vinaBrewTables.length === 0 && (
        <div className="px-3 py-2 border-b border-white/5">
          <button
            onClick={onSeed} disabled={seeding}
            className="w-full text-[10px] btn-primary py-1 rounded disabled:opacity-50"
          >
            {seeding ? 'Seeding…' : '⊕ Load VINA BREW dataset'}
          </button>
        </div>
      )}

      {tables.length === 0 && !seeding && (
        <p className="text-[10px] text-gray-600 p-3 leading-relaxed">
          {MSG.emptyDatasets}
        </p>
      )}

      {vinaBrewTables.length > 0 && (
        <RelationsPanel onInsert={onInsert} />
      )}

      {tables.map(t => (
        <div key={t.file_id} className="border-b border-white/5">
          <button
            onClick={() => toggle(t.table_name)}
            className="w-full flex items-center gap-1.5 px-3 py-2 hover:bg-white/3 transition-colors text-left group"
          >
            {open[t.table_name]
              ? <ChevronDown  size={11} className="text-gray-600 flex-shrink-0" />
              : <ChevronRight size={11} className="text-gray-600 flex-shrink-0" />}
            <Database size={11} className="text-data flex-shrink-0" />
            <span className="text-[11px] text-gray-300 font-mono truncate flex-1">{t.table_name}</span>
            {t.source === 'vina_brew' && (
              <Tag size={9} className="text-analytics/60 flex-shrink-0 mr-0.5" aria-label="VINA BREW" />
            )}
            <button
              onClick={e => { e.stopPropagation(); onInsert(t.table_name) }}
              className="opacity-0 group-hover:opacity-100 text-[10px] text-gray-600 hover:text-gray-300 px-1"
              title="Insert table name"
            >↵</button>
            {t.source !== 'vina_brew' && (
              <button
                onClick={e => { e.stopPropagation(); onDelete(t.file_id, t.table_name) }}
                className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-danger transition-colors px-1"
                title="Delete dataset"
              ><Trash2 size={11} /></button>
            )}
          </button>
          <p className="px-7 pb-1 text-[10px] text-gray-600">
            {t.rows.toLocaleString()} rows · {t.cols} cols
            {t.source === 'vina_brew' && (
              <span className="ml-1 text-analytics/50">[VINA BREW]</span>
            )}
          </p>

          {open[t.table_name] && (
            <div className="pb-2">
              {t.columns.map(c => {
                const desc = SCHEMA_META[t.table_name]?.[c.name]
                return (
                  <button
                    key={c.name}
                    onClick={() => onInsert(c.name)}
                    className="w-full flex flex-col px-7 py-1 hover:bg-white/3 transition-colors text-left gap-0.5"
                  >
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-mono truncate flex-1 ${
                        isNumericCol(c.dtype) ? 'text-analytics' : 'text-gray-200'
                      }`}>{c.name}</span>
                      <span className="text-[9px] text-gray-600 flex-shrink-0">
                        {c.dtype.replace('DataType.','')}
                      </span>
                    </div>
                    {desc && (
                      <p className="text-[9px] text-gray-600 leading-relaxed pl-0 truncate">{desc}</p>
                    )}
                  </button>
                )
              })}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// ── ResultTable ───────────────────────────────────────────────────────────────
function ResultTable({ result }: { result: SqlResult }) {
  const display = result.rows.slice(0, 1000)
  return (
    <div className="overflow-auto flex-1 min-h-0">
      <p className="text-[10px] text-gray-600 px-3 py-1.5 border-b border-white/5 flex gap-3 flex-shrink-0">
        <span>{result.rows.length.toLocaleString()} rows</span>
        <span>{result.duration_ms.toFixed(1)}ms · DuckDB</span>
        {result.tables.length > 0 && (
          <span className="text-gray-700">tables: {result.tables.join(', ')}</span>
        )}
        {result.rows.length > 1000 && <span className="text-yellow-500">showing first 1,000</span>}
      </p>
      <table className="w-full text-xs border-collapse">
        <thead className="sticky top-0 bg-[#0d1117]">
          <tr>
            {result.columns.map(c => (
              <th key={c} className="text-left text-[10px] text-gray-500 uppercase tracking-wider px-3 py-1.5 border-b border-white/5 whitespace-nowrap">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {display.map((row, i) => (
            <tr key={i} className="hover:bg-white/3 transition-colors">
              {(row as unknown[]).map((cell, j) => (
                <td key={j} className="px-3 py-1.5 text-gray-300 border-b border-white/3 whitespace-nowrap max-w-[240px] truncate">
                  {cell == null
                    ? <span className="text-gray-600 italic">null</span>
                    : typeof cell === 'number' ? fmtNum(cell) : String(cell)
                  }
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function SqlSandbox() {
  const [tables,        setTables]        = useState<TableInfo[]>([])
  const [tablesLoading, setTablesLoading] = useState(true)
  const [sql,           setSql]           = useState('SELECT *\nFROM dim_product\nLIMIT 20')
  const [result,        setResult]        = useState<SqlResult | null>(null)
  const [running,       setRunning]       = useState(false)
  const [error,         setError]         = useState<{ type: string; msg: string } | null>(null)
  const [history,       setHistory]       = useState<HistoryEntry[]>(loadHistory)
  const [showHist,      setShowHist]      = useState(false)
  const [uploading,     setUploading]     = useState(false)
  const [seeding,       setSeeding]       = useState(false)
  const [copied,        setCopied]        = useState(false)
  const [selectedExId,  setSelectedExId]  = useState<string | null>(null)
  const [showSuggest,   setShowSuggest]   = useState(false)
  const [progress,      setProgress]      = useState<Progress>(loadProgress)

  const fileInputRef  = useRef<HTMLInputElement>(null)
  const navigate      = useNavigate()
  const [sidebarWidth,  setSidebarWidth]  = useState(260)
  const [sendingToML,   setSendingToML]   = useState(false)
  const [mlSent,        setMlSent]        = useState(false)
  const isDragging    = useRef(false)

  const onDragStart = useCallback((e: React.MouseEvent) => {
    isDragging.current = true
    const startX = e.clientX
    const startW = sidebarWidth
    const onMove = (mv: MouseEvent) => {
      if (!isDragging.current) return
      const next = Math.min(480, Math.max(180, startW + mv.clientX - startX))
      setSidebarWidth(next)
    }
    const onUp = () => { isDragging.current = false; window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [sidebarWidth])

  async function loadTables() {
    setTablesLoading(true)
    try { setTables(await fetchTables()) } catch { /* ignore */ }
    finally { setTablesLoading(false) }
  }

  useEffect(() => { loadTables() }, [])

  useEffect(() => {
    const injected = localStorage.getItem('sql_sandbox_inject')
    if (injected) {
      setSql(injected)
      localStorage.removeItem('sql_sandbox_inject')
    }
  }, [])

  async function handleRun() {
    if (!sql.trim()) return
    setRunning(true); setError(null); setResult(null)
    try {
      const r = await runSql(sql)
      setResult(r)
      const entry: HistoryEntry = { sql, ts: Date.now(), rows: r.rows.length, ms: r.duration_ms }
      const h = [entry, ...history].slice(0, MAX_HISTORY)
      setHistory(h); saveHistory(h)
    } catch (e: unknown) {
      const raw = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? MSG.queryFailed
      setError(parseError(raw))
    } finally { setRunning(false) }
  }

  async function handleSeed() {
    setSeeding(true)
    try { await seedVinaBrew(); await loadTables() }
    catch { /* ignore */ }
    finally { setSeeding(false) }
  }

  async function handleCheckExercise(exerciseId: string, expectedColumns: string[]) {
    try {
      const res = await checkExercise({ exercise_id: exerciseId, sql, expected_columns: expectedColumns })
      const updated = { ...progress }
      updated[exerciseId] = res.passed ? 'passed' : 'attempted'
      setProgress(updated)
      saveProgress(updated)
      return res
    } catch {
      return { passed: false, actual_columns: [], expected_columns: expectedColumns, error: MSG.requestFailed }
    }
  }


  const insertAtCursor = useCallback((text: string) => {
    setSql(s => s + '\n' + text)
  }, [])

  async function handleUpload(file: File) {
    setUploading(true)
    try { await uploadFile(file); await loadTables() }
    catch { /* ignore */ }
    finally { setUploading(false) }
  }

  async function handleDelete(fileId: string, name: string) {
    if (!confirm(MSG.confirmDelete(`bảng "${name}"`))) return
    try { await deleteDataset(fileId); await loadTables() }
    catch { /* ignore */ }
  }

  async function sendToMlStudio() {
    if (!result) return
    setSendingToML(true)
    try {
      const escape = (v: unknown) => {
        const s = v == null ? '' : String(v)
        return s.includes(',') || s.includes('"') || s.includes('\n')
          ? `"${s.replace(/"/g, '""')}"` : s
      }
      const csv = [
        result.columns.join(','),
        ...result.rows.map(r => (r as unknown[]).map(escape).join(',')),
      ].join('\n')
      const ts   = new Date().toISOString().slice(0,19).replace(/[-T:]/g, '_')
      const name = (result.tables[0] ?? 'query_result') + `_${ts}.csv`
      const file = new File([csv], name, { type: 'text/csv' })
      await uploadFile(file)
      setMlSent(true)
      setTimeout(() => { setMlSent(false); navigate('/analytics/ml') }, 800)
    } catch { /* ignore */ }
    finally { setSendingToML(false) }
  }

  async function copyResult() {
    if (!result) return
    const tsv = [
      result.columns.join('\t'),
      ...result.rows.map(r => (r as unknown[]).join('\t')),
    ].join('\n')
    await navigator.clipboard.writeText(tsv)
    setCopied(true); setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="flex h-screen overflow-hidden">

      {/* ── Left sidebar: schema + metrics dict + exercises ── */}
      <div className="border-r border-white/5 flex flex-col flex-shrink-0 overflow-hidden" style={{ width: sidebarWidth }}>
        <div className="flex items-center justify-between px-3 py-2.5 border-b border-white/5 flex-shrink-0">
          <span className="text-[11px] font-semibold text-gray-300">Tables</span>
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-300 transition-colors disabled:opacity-50"
          >
            <Upload size={11} /> {uploading ? 'Uploading…' : 'Upload'}
          </button>
          <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls" className="hidden"
            onChange={e => { const f = e.target.files?.[0]; if (f) handleUpload(f); e.target.value = '' }} />
        </div>

        <div className="flex-1 overflow-y-auto min-h-0">
          <SchemaPanel
            tables={tables} loading={tablesLoading}
            onInsert={insertAtCursor} onDelete={handleDelete}
            onSeed={handleSeed} seeding={seeding}
          />
        </div>

        <MetricsDictPanel />

        <ExercisesPanel
          onInject={setSql}
          selectedId={selectedExId}
          onSelect={id => { setSelectedExId(id); if (id) setShowSuggest(true) }}
          progress={progress}
          onCheck={async (id, cols) => {
            const res = await handleCheckExercise(id, cols)
            return res
          }}
        />

        {/* Shortcuts */}
        <div className="border-t border-white/5 p-3 flex flex-col gap-1.5 flex-shrink-0">
          <p className="text-[9px] text-gray-600 uppercase tracking-wider mb-0.5">Shortcuts</p>
          {[
            ['Shift+↵', 'Run query'],
            ['Tab',    '2-space indent'],
            ['Click col', 'Insert name'],
          ].map(([k, v]) => (
            <div key={k} className="flex justify-between text-[10px]">
              <span className="text-gray-600 font-mono">{k}</span>
              <span className="text-gray-700">{v}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Drag handle ── */}
      <div
        onMouseDown={onDragStart}
        className="w-1 flex-shrink-0 cursor-col-resize hover:bg-analytics/40 active:bg-analytics/60 transition-colors"
      />

      {/* ── Center: editor + results ── */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">

        {/* Toolbar */}
        <div className="flex items-center gap-2 px-3 py-1.5 border-b border-white/5 bg-white/2 flex-shrink-0">
          <span className="text-[10px] text-gray-600 font-mono flex-1">SQL Editor · DuckDB</span>
          <button
            onClick={() => setShowHist(h => !h)}
            className={`flex items-center gap-1 text-[10px] px-2 py-0.5 rounded border transition-all ${
              showHist
                ? 'text-analytics border-analytics/30 bg-analytics/10'
                : 'text-gray-600 border-transparent hover:text-gray-400'
            }`}
          >
            <Clock size={10} /> History ({history.length})
          </button>
          <button
            onClick={() => setShowSuggest(s => !s)}
            className={`flex items-center gap-1 text-[10px] px-2 py-0.5 rounded border transition-all ${
              showSuggest
                ? 'text-yellow-400 border-yellow-400/30 bg-yellow-400/10'
                : 'text-gray-600 border-transparent hover:text-gray-400'
            }`}
          >
            <Lightbulb size={10} /> Suggest
          </button>
          <button
            onClick={handleRun} disabled={running}
            className="btn-primary flex items-center gap-1.5 text-xs disabled:opacity-50"
          >
            <Play size={11} fill="currentColor" />
            {running ? 'Running…' : 'Run'}
            <span className="text-[10px] opacity-50 font-normal">Shift+↵</span>
          </button>
        </div>

        {/* SQL editor */}
        <div className="border-b border-white/5 flex-shrink-0" style={{ height: 220 }}>
          <SqlEditor value={sql} onChange={setSql} onRun={handleRun} />
        </div>

        {/* History panel */}
        {showHist && (
          <div className="border-b border-white/5 bg-[#0d1117] max-h-44 overflow-y-auto flex-shrink-0">
            {history.length === 0
              ? <p className="text-[10px] text-gray-600 p-3">{MSG.emptyHistory}</p>
              : history.map((h, i) => (
                  <div key={i}
                    className="flex items-start gap-2 px-3 py-2 hover:bg-white/3 border-b border-white/3 cursor-pointer group"
                    onClick={() => { setSql(h.sql); setShowHist(false) }}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-[10px] font-mono text-gray-400 truncate">
                        {h.sql.replace(/\s+/g,' ').trim()}
                      </p>
                      <p className="text-[9px] text-gray-700 mt-0.5">
                        {new Date(h.ts).toLocaleTimeString('vi-VN')} · {h.rows.toLocaleString()} rows · {h.ms.toFixed(0)}ms
                      </p>
                    </div>
                    <button
                      onClick={e => {
                        e.stopPropagation()
                        const h2 = history.filter((_,j) => j!==i)
                        setHistory(h2); saveHistory(h2)
                      }}
                      className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-danger flex-shrink-0"
                    ><Trash2 size={11} /></button>
                  </div>
                ))
            }
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div className={`px-4 py-2 border-b flex-shrink-0 ${
            error.type === 'syntax'  ? 'bg-red-950/30 border-red-900/30' :
            error.type === 'field'   ? 'bg-orange-950/30 border-orange-900/30' :
            error.type === 'table'   ? 'bg-yellow-950/30 border-yellow-900/30' :
            'bg-danger/10 border-danger/20'
          }`}>
            <p className="text-danger text-xs font-mono whitespace-pre-wrap">{error.msg}</p>
          </div>
        )}

        {/* Results */}
        {result ? (
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="flex items-center justify-between px-3 py-1 border-b border-white/5 bg-white/2 flex-shrink-0">
              <span className="text-[10px] text-gray-600">Results</span>
              <div className="flex items-center gap-3">
                <button onClick={copyResult}
                  className="flex items-center gap-1 text-[10px] text-gray-600 hover:text-gray-300 transition-colors">
                  {copied ? <Check size={10} className="text-green-400" /> : <Copy size={10} />}
                  {copied ? 'Copied!' : 'Copy TSV'}
                </button>
                <button
                  onClick={sendToMlStudio}
                  disabled={sendingToML}
                  className="flex items-center gap-1 text-[10px] text-analytics hover:text-analytics/80 transition-colors disabled:opacity-50"
                  title="Upload result as CSV to ML Studio"
                >
                  {mlSent
                    ? <><Check size={10} className="text-green-400" /> Sent!</>
                    : sendingToML
                      ? <>Sending…</>
                      : <><FlaskConical size={10} /> ML Studio</>}
                </button>
              </div>
            </div>
            <ResultTable result={result} />
          </div>
        ) : !error && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center flex flex-col items-center gap-3">
              <Database size={36} className="text-gray-700" />
              <p className="text-gray-600 text-sm">{MSG.runToSeeResults}</p>
              {tables.length > 0 && (
                <p className="text-gray-700 text-xs font-mono">
                  {tables.map(t => t.table_name).join(' · ')}
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── Right: Query Suggest panel (toggle) ── */}
      {showSuggest && (
        <QuerySuggestPanel
          selectedExId={selectedExId}
          onClose={() => setShowSuggest(false)}
        />
      )}
    </div>
  )
}
