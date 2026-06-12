# Automation (Frontend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the React UI for the Automation feature: a master–detail page where the user creates/edits declarative `JobConfig`s, previews shaped rows, runs a job (with live status polling), and views the generated Python + SQL — all wired to the backend `/api/automation` endpoints.

**Architecture:** One page `pages/data/Automation.tsx` (2 columns: `JobList` left, `JobForm` + action toolbar + result panel right) composed of focused components under `components/automation/`. A thin axios module `api/automation.ts` mirrors the 8 backend endpoints. Types added to `types.ts` are 1:1 with the backend Pydantic models. "Show Code" reuses the existing `components/ml/CodePanel.tsx`, generalized with an optional `language` prop so it renders both Python and SQL.

**Tech Stack:** React 19, react-router-dom 7, TypeScript ~5.7, Tailwind (utility classes in `index.css`), axios (`api/client.ts`), lucide-react icons, Vite. **No frontend test framework exists** — verification is the TypeScript compiler (`npx tsc -b --noEmit`) plus targeted manual checks.

**Spec:** `docs/superpowers/specs/2026-06-04-automation-design.md` (§6.6 API contract, §7 Frontend Design, §8 Error Handling).
**Scope of THIS plan:** Frontend only (spec §7). The backend (spec §6, §8–§11) is already implemented per `docs/superpowers/plans/2026-06-04-automation-backend.md`.

### Conventions
- **No test runner on the frontend.** The TDD "write a failing test" step is replaced by **type-checking**: after each file, run `npx tsc -b --noEmit` from `frontend/` and require zero errors. Real visual/behavioural verification happens once routing is wired (Task 10) and end-to-end (Task 11).
- All `npx`/`npm` commands run **from `frontend/`**.
- API base URL is `/api` (`api/client.ts`), so endpoint paths in `api/automation.ts` start at `/automation/...` → resolve to `/api/automation/...`.
- **Stage ONLY the files listed in each task.** Never `git add -A` / `git add .`. Never stage `.env` or unrelated work-in-progress files.
- **Do NOT touch** unrelated do-not-touch files: `frontend/src/api/sql.ts`, `frontend/src/components/sql/*`, `frontend/src/data/*`, the SQL Sandbox / Snippet / Fabric / Action Plan pages, or `.claude/*`. This plan only creates files under `components/automation/`, `api/automation.ts`, `pages/data/Automation.tsx`, and makes additive edits to `types.ts`, `components/ml/CodePanel.tsx`, `components/layout/Sidebar.tsx`, `App.tsx`.
- Mirror existing house patterns: master–detail page (`pages/work/QuickNotes.tsx`), CRUD axios module (`api/notes.ts`), form with `initial?` + `onSaved`/`onCancel` (`components/notes/NoteForm.tsx`), utility classes (`.glass-card .btn-primary .btn-ghost .btn-danger .input-base .badge`).

---

## File Structure

| File | Responsibility |
|------|----------------|
| `frontend/src/types.ts` *(modify)* | Add Automation types (1:1 with backend models) |
| `frontend/src/api/automation.ts` *(create)* | 8 axios calls: list/get/create/update/delete/preview/run/code |
| `frontend/src/components/ml/CodePanel.tsx` *(modify)* | Add optional `language: 'python' \| 'sql'` (backward-compatible) |
| `frontend/src/components/automation/CodeViewer.tsx` *(create)* | Python/SQL tabs wrapping `CodePanel` |
| `frontend/src/components/automation/JobList.tsx` *(create)* | Job list + status badges + "New" button |
| `frontend/src/components/automation/PreviewPanel.tsx` *(create)* | N-row preview table |
| `frontend/src/components/automation/RunStatus.tsx` *(create)* | Poll `GET /jobs/{id}` every ~2s until `last_status != 'running'` |
| `frontend/src/components/automation/JobForm.tsx` *(create)* | Full `JobConfig` editor (source / SQL / export / notify) |
| `frontend/src/pages/data/Automation.tsx` *(create)* | Master–detail page wiring all of the above |
| `frontend/src/components/layout/Sidebar.tsx` *(modify)* | Add `Workflow` icon + nav item in the `data` group |
| `frontend/src/App.tsx` *(modify)* | Lazy import + nested route `data/automation` |

**Naming contract (used across tasks):**
- **Types:** `RestAuthType, RestAuth, Pagination, RestSource, ExportFormat, ExportSpec, EmailSpec, NotifySpec, JobConfig, RunStatusValue, RunResult, AutomationJob, PreviewResult, JobCode`.
- **API fns:** `listJobs, getJob, createJob, updateJob, deleteJob, previewJob, runJob, getJobCode`.
- **Components:** `JobList, JobForm, PreviewPanel, RunStatus, CodeViewer` (default exports).
- **Page:** `Automation` (default export).

---

## Task 1: Automation types in `types.ts`

**Files:**
- Modify: `frontend/src/types.ts` (append a new section at end of file)

- [ ] **Step 1: Append the Automation types**

Append to the very end of `frontend/src/types.ts` (these mirror `backend/automation/models.py` exactly):

```ts
// ─── Automation ───────────────────────────────────────────────────────────────

export type RestAuthType = 'none' | 'api_key' | 'basic' | 'bearer'

export interface RestAuth {
  type: RestAuthType
  header_name?: string | null   // api_key: header to set (e.g. "X-API-Key")
  value_ref?: string | null     // api_key/bearer: env-var NAME holding the secret
  user_ref?: string | null      // basic: env-var name for username
  pass_ref?: string | null      // basic: env-var name for password
}

export interface Pagination {
  param: string                 // query param name, e.g. "page"
  start: number                 // first page number
}

export interface RestSource {
  url: string
  method: 'GET'
  headers: Record<string, string>   // values may contain ${VAR}
  params: Record<string, string>
  auth: RestAuth
  records_path: string              // dotted path to the array, e.g. "data.items" ("" = root)
  pagination: Pagination | null
  timeout_seconds: number
  max_retries: number
}

export type ExportFormat = 'duckdb' | 'parquet' | 'csv' | 'xlsx'

export interface ExportSpec {
  formats: ExportFormat[]
  dest_dir: string
  duckdb_mode: 'overwrite' | 'append'
  xlsx_row_guard: number
}

export interface EmailSpec {
  enabled: boolean
  recipients: string[]
  attach_max_bytes: number
}

export interface NotifySpec {
  discord_enabled: boolean
  email: EmailSpec
}

export interface JobConfig {
  name: string
  source: RestSource
  shape_sql: string             // DuckDB SQL over `raw`; "" = passthrough
  export: ExportSpec
  notify: NotifySpec
}

export type RunStatusValue = 'ok' | 'warning' | 'error' | 'running'

export interface RunResult {
  status: RunStatusValue
  rows: number
  duration_seconds: number
  output_files: string[]
  error: string | null
}

export interface AutomationJob {
  id: string
  config: JobConfig
  last_status: string | null
  last_run_at: string | null
  last_rows: number | null
  last_error: string | null
  created: string
  updated: string
}

export interface PreviewResult {     // POST /jobs/{id}/preview
  columns: string[]
  rows: unknown[][]
}

export interface JobCode {           // GET /jobs/{id}/code
  python: string
  sql: string
}
```

- [ ] **Step 2: Type-check**

Run (from `frontend/`): `npx tsc -b --noEmit`
Expected: PASS (no errors). Types are not yet consumed; this only confirms valid syntax.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types.ts
git commit -m "feat(automation): add frontend types mirroring backend models"
```

---

## Task 2: API module `api/automation.ts`

**Files:**
- Create: `frontend/src/api/automation.ts`

- [ ] **Step 1: Write the module**

Create `frontend/src/api/automation.ts` (mirrors `api/notes.ts` axios pattern; `previewJob` uses a longer per-call timeout like `api/ml.ts`'s upload):

```ts
import client from './client'
import type { AutomationJob, JobConfig, PreviewResult, JobCode } from '../types'

export async function listJobs(): Promise<AutomationJob[]> {
  const { data } = await client.get<AutomationJob[]>('/automation/jobs')
  return data
}

export async function getJob(id: string): Promise<AutomationJob> {
  const { data } = await client.get<AutomationJob>(`/automation/jobs/${id}`)
  return data
}

export async function createJob(config: JobConfig): Promise<AutomationJob> {
  const { data } = await client.post<AutomationJob>('/automation/jobs', config)
  return data
}

export async function updateJob(id: string, config: JobConfig): Promise<AutomationJob> {
  const { data } = await client.put<AutomationJob>(`/automation/jobs/${id}`, config)
  return data
}

export async function deleteJob(id: string): Promise<void> {
  await client.delete(`/automation/jobs/${id}`)
}

export async function previewJob(id: string, n_rows = 100): Promise<PreviewResult> {
  const { data } = await client.post<PreviewResult>(
    `/automation/jobs/${id}/preview`,
    { n_rows },
    { timeout: 120_000 },          // a preview hits the live REST API; allow more time
  )
  return data
}

export async function runJob(id: string): Promise<{ status: string }> {
  const { data } = await client.post<{ status: string }>(`/automation/jobs/${id}/run`, {})
  return data
}

export async function getJobCode(id: string): Promise<JobCode> {
  const { data } = await client.get<JobCode>(`/automation/jobs/${id}/code`)
  return data
}
```

- [ ] **Step 2: Type-check**

Run (from `frontend/`): `npx tsc -b --noEmit`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/automation.ts
git commit -m "feat(automation): add api/automation.ts axios client"
```

---

## Task 3: Generalize `CodePanel` with a `language` prop

**Why:** Spec §7 says Show Code reuses `CodePanel` for **Python + SQL** tabs, but the current `CodePanel` hardcodes the "Python Code" header, the "Download .py" button, and a Python-only highlighter. Add an optional `language` prop (default `'python'`) so the same component renders SQL correctly. The change is **backward-compatible** — existing ML callers pass no `language` and behave identically.

**Files:**
- Modify: `frontend/src/components/ml/CodePanel.tsx` (replace whole file)

- [ ] **Step 1: Replace the file contents**

Replace the entire contents of `frontend/src/components/ml/CodePanel.tsx` with:

```tsx
import { useState } from 'react'
import { Code2, Copy, Check, Download, ChevronDown, ChevronUp } from 'lucide-react'

interface Props {
  code: string
  filename?: string            // e.g. "stats_analysis.py"
  defaultOpen?: boolean
  language?: 'python' | 'sql'  // drives header label, download ext + MIME, highlighter
}

export default function CodePanel({ code, filename, defaultOpen = false, language = 'python' }: Props) {
  const [open,   setOpen]   = useState(defaultOpen)
  const [copied, setCopied] = useState(false)

  const ext    = language === 'sql' ? 'sql' : 'py'
  const mime   = language === 'sql' ? 'text/sql' : 'text/x-python'
  const dlName = filename ?? `analysis.${ext}`
  const label  = language === 'sql' ? 'SQL Code' : 'Python Code'

  function handleCopy() {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  function handleDownload() {
    const blob = new Blob([code], { type: mime })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url; a.download = dlName; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="border border-white/10 rounded-lg overflow-hidden">
      {/* Header toggle */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-[#161b22] hover:bg-white/5 transition-colors text-left"
      >
        <Code2 size={12} className="text-analytics flex-shrink-0" />
        <span className="text-[11px] font-semibold text-gray-300 flex-1">{label}</span>
        <span className="text-[9px] text-gray-600 mr-1">{code.split('\n').length} lines</span>
        {open
          ? <ChevronUp   size={11} className="text-gray-600" />
          : <ChevronDown size={11} className="text-gray-600" />}
      </button>

      {open && (
        <div className="bg-[#0d1117]">
          {/* Toolbar */}
          <div className="flex items-center justify-end gap-3 px-3 py-1.5 border-b border-white/5">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-300 transition-colors"
            >
              {copied ? <Check size={10} className="text-green-400" /> : <Copy size={10} />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <button
              onClick={handleDownload}
              className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-300 transition-colors"
            >
              <Download size={10} /> Download .{ext}
            </button>
          </div>

          {/* Code block */}
          <pre className="text-[11px] font-mono text-gray-300 leading-relaxed p-4 overflow-x-auto whitespace-pre">
            {highlight(code, language)}
          </pre>
        </div>
      )}
    </div>
  )
}

// Minimal keyword highlight — returns React nodes
function highlight(code: string, language: 'python' | 'sql' = 'python') {
  const PY_KEYWORDS = /\b(import|from|as|def|class|return|for|in|if|else|elif|not|and|or|True|False|None|with|pass|raise|try|except|finally|lambda|yield|async|await|print)\b/g
  const PY_BUILTINS = /\b(len|range|list|dict|str|int|float|bool|type|isinstance|enumerate|zip|map|filter|sorted|sum|min|max|abs|round|open|np|pl|pd|stats)\b/g
  const PY_COMMENTS = /(#.*$)/gm

  const SQL_KEYWORDS = /\b(SELECT|FROM|WHERE|GROUP|BY|ORDER|HAVING|LIMIT|OFFSET|JOIN|LEFT|RIGHT|INNER|OUTER|FULL|CROSS|ON|USING|AS|AND|OR|NOT|IN|IS|NULL|LIKE|ILIKE|BETWEEN|CASE|WHEN|THEN|ELSE|END|DISTINCT|UNION|ALL|EXCEPT|INTERSECT|WITH|INSERT|INTO|VALUES|UPDATE|SET|DELETE|CREATE|TABLE|VIEW|DROP|ASC|DESC|OVER|PARTITION|QUALIFY)\b/gi
  const SQL_BUILTINS = /\b(COUNT|SUM|AVG|MIN|MAX|ROUND|CAST|COALESCE|NULLIF|ROW_NUMBER|RANK|DENSE_RANK|LAG|LEAD|DATE_TRUNC|STRFTIME|EXTRACT|LENGTH|UPPER|LOWER|TRIM|CONCAT)\b/gi
  const SQL_COMMENTS = /(--.*$)/gm

  const KEYWORDS = language === 'sql' ? SQL_KEYWORDS : PY_KEYWORDS
  const BUILTINS = language === 'sql' ? SQL_BUILTINS : PY_BUILTINS
  const COMMENTS = language === 'sql' ? SQL_COMMENTS : PY_COMMENTS
  const STRINGS  = /("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')/g
  const NUMBERS  = /\b(\d+\.?\d*)\b/g

  const lines = code.split('\n')
  return lines.map((line, i) => {
    const parts: React.ReactNode[] = []
    let last = 0
    const tokens: { start: number; end: number; type: string }[] = []

    const addTokens = (re: RegExp, type: string) => {
      let m: RegExpExecArray | null
      const r = new RegExp(re.source, re.flags.replace('g','') + 'g')
      while ((m = r.exec(line)) !== null) {
        tokens.push({ start: m.index, end: m.index + m[0].length, type })
      }
    }

    addTokens(COMMENTS, 'comment')
    addTokens(STRINGS,  'string')
    addTokens(KEYWORDS, 'keyword')
    addTokens(BUILTINS, 'builtin')
    addTokens(NUMBERS,  'number')

    tokens.sort((a, b) => a.start - b.start)

    const used: boolean[] = new Array(line.length).fill(false)
    const clean: typeof tokens = []
    for (const t of tokens) {
      if (!used.slice(t.start, t.end).some(Boolean)) {
        clean.push(t)
        for (let j = t.start; j < t.end; j++) used[j] = true
      }
    }
    clean.sort((a, b) => a.start - b.start)

    for (const t of clean) {
      if (last < t.start) parts.push(line.slice(last, t.start))
      const text = line.slice(t.start, t.end)
      const cls =
        t.type === 'keyword' ? 'text-purple-400' :
        t.type === 'builtin' ? 'text-blue-400'   :
        t.type === 'string'  ? 'text-amber-300'  :
        t.type === 'comment' ? 'text-gray-600 italic' :
        t.type === 'number'  ? 'text-green-400'  : ''
      parts.push(<span key={t.start} className={cls}>{text}</span>)
      last = t.end
    }
    if (last < line.length) parts.push(line.slice(last))

    return <span key={i}>{parts}{'\n'}</span>
  })
}
```

- [ ] **Step 2: Type-check (and confirm existing ML callers still compile)**

Run (from `frontend/`): `npx tsc -b --noEmit`
Expected: PASS. The new prop is optional, so existing `<CodePanel code=… filename=… />` usages in ML components are unaffected.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ml/CodePanel.tsx
git commit -m "refactor(ml): make CodePanel language-aware (python|sql), backward-compatible"
```

---

## Task 4: `CodeViewer.tsx` (Python/SQL tabs)

**Files:**
- Create: `frontend/src/components/automation/CodeViewer.tsx`

- [ ] **Step 1: Write the component**

Create `frontend/src/components/automation/CodeViewer.tsx`:

```tsx
import { useState } from 'react'
import CodePanel from '../ml/CodePanel'

interface Props {
  python: string
  sql: string
  jobName: string
}

export default function CodeViewer({ python, sql, jobName }: Props) {
  const [tab, setTab] = useState<'python' | 'sql'>('python')
  const safe = jobName.trim().replace(/[^a-zA-Z0-9_-]+/g, '_') || 'job'

  return (
    <div className="glass-card p-3">
      <div className="flex gap-1 mb-2">
        {(['python', 'sql'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              tab === t ? 'bg-accent/15 text-accent' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {t === 'python' ? 'Python' : 'SQL'}
          </button>
        ))}
      </div>

      {tab === 'python'
        ? <CodePanel code={python} language="python" filename={`${safe}.py`} defaultOpen />
        : <CodePanel code={sql || '-- (passthrough: no shaping SQL)'} language="sql" filename={`${safe}.sql`} defaultOpen />}
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

Run (from `frontend/`): `npx tsc -b --noEmit`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/automation/CodeViewer.tsx
git commit -m "feat(automation): add CodeViewer (Python/SQL tabs)"
```

---

## Task 5: `JobList.tsx`

**Files:**
- Create: `frontend/src/components/automation/JobList.tsx`

- [ ] **Step 1: Write the component**

Create `frontend/src/components/automation/JobList.tsx`:

```tsx
import { Plus } from 'lucide-react'
import type { AutomationJob } from '../../types'

interface Props {
  jobs: AutomationJob[]
  selectedId: string | null
  onSelect: (job: AutomationJob) => void
  onNew: () => void
}

const STATUS_STYLE: Record<string, string> = {
  ok:      'bg-green-500/15 text-green-400',
  error:   'bg-danger/15 text-danger',
  warning: 'bg-amber-500/15 text-amber-400',
  running: 'bg-accent/15 text-accent animate-pulse',
}

function StatusBadge({ status }: { status: string | null }) {
  if (!status) return <span className="badge text-gray-500">never run</span>
  const cls = STATUS_STYLE[status] ?? 'bg-white/5 text-gray-400'
  return <span className={`badge ${cls}`}>{status}</span>
}

export default function JobList({ jobs, selectedId, onSelect, onNew }: Props) {
  return (
    <div className="w-72 flex-shrink-0 border-r border-white/5 flex flex-col h-full">
      <div className="px-4 pt-4 pb-3 border-b border-white/5 flex items-center justify-between flex-shrink-0">
        <h2 className="text-sm font-semibold text-white">Automation Jobs</h2>
        <button onClick={onNew} className="btn-primary text-xs px-2 py-1 flex items-center gap-1">
          <Plus size={13} /> New
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {jobs.length === 0 && (
          <p className="text-gray-600 text-xs text-center mt-8">No jobs yet — click "New".</p>
        )}
        {jobs.map(job => (
          <button
            key={job.id}
            onClick={() => onSelect(job)}
            className={`w-full text-left px-3 py-2.5 rounded-lg mb-1 transition-colors ${
              selectedId === job.id
                ? 'bg-white/5 border border-white/10'
                : 'hover:bg-white/5 border border-transparent'
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm text-gray-200 truncate">{job.config.name || '(unnamed)'}</span>
              <StatusBadge status={job.last_status} />
            </div>
            <div className="text-[10px] text-gray-600 mt-1 flex gap-2">
              <span>{job.last_run_at ? job.last_run_at.slice(0, 16).replace('T', ' ') : '—'}</span>
              {job.last_rows != null && <span>· {job.last_rows} rows</span>}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

Run (from `frontend/`): `npx tsc -b --noEmit`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/automation/JobList.tsx
git commit -m "feat(automation): add JobList with status badges"
```

---

## Task 6: `PreviewPanel.tsx`

**Files:**
- Create: `frontend/src/components/automation/PreviewPanel.tsx`

- [ ] **Step 1: Write the component**

Create `frontend/src/components/automation/PreviewPanel.tsx`:

```tsx
import type { PreviewResult } from '../../types'

interface Props {
  data: PreviewResult
}

export default function PreviewPanel({ data }: Props) {
  if (data.columns.length === 0) {
    return <p className="text-gray-500 text-xs p-3">Preview returned no columns.</p>
  }
  return (
    <div className="glass-card overflow-hidden">
      <div className="px-3 py-2 border-b border-white/5 text-[11px] text-gray-400">
        Preview · {data.rows.length} rows × {data.columns.length} cols
      </div>
      <div className="overflow-auto max-h-80">
        <table className="w-full text-[11px] border-collapse">
          <thead className="sticky top-0 bg-tertiary">
            <tr>
              {data.columns.map(c => (
                <th key={c} className="text-left px-2 py-1.5 text-gray-400 font-medium border-b border-white/5 whitespace-nowrap">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, i) => (
              <tr key={i} className="hover:bg-white/5">
                {row.map((cell, j) => (
                  <td key={j} className="px-2 py-1 text-gray-300 border-b border-white/5 whitespace-nowrap max-w-xs truncate">
                    {cell == null ? <span className="text-gray-600">null</span> : String(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

Run (from `frontend/`): `npx tsc -b --noEmit`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/automation/PreviewPanel.tsx
git commit -m "feat(automation): add PreviewPanel table"
```

---

## Task 7: `RunStatus.tsx` (polling)

**Files:**
- Create: `frontend/src/components/automation/RunStatus.tsx`

- [ ] **Step 1: Write the component**

Create `frontend/src/components/automation/RunStatus.tsx`. It polls `GET /jobs/{id}` every 2s until `last_status !== 'running'`, then calls `onDone(job)`. Cleanup stops polling on unmount; a ref keeps `onDone` fresh without restarting the effect:

```tsx
import { useEffect, useRef, useState } from 'react'
import { Loader2, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react'
import type { AutomationJob } from '../../types'
import { getJob } from '../../api/automation'

interface Props {
  jobId: string
  onDone: (job: AutomationJob) => void
}

export default function RunStatus({ jobId, onDone }: Props) {
  const [job,   setJob]   = useState<AutomationJob | null>(null)
  const [error, setError] = useState('')
  const onDoneRef = useRef(onDone)
  onDoneRef.current = onDone

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout>

    async function poll() {
      try {
        const j = await getJob(jobId)
        if (!alive) return
        setJob(j)
        if (j.last_status === 'running') {
          timer = setTimeout(poll, 2000)
        } else {
          onDoneRef.current(j)
        }
      } catch (err: unknown) {
        if (!alive) return
        const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
        setError(typeof detail === 'string' ? detail : 'Failed to poll job status')
      }
    }

    poll()
    return () => { alive = false; clearTimeout(timer) }
  }, [jobId])

  if (error) {
    return <p className="text-danger text-xs bg-danger/10 border border-danger/20 px-3 py-2 rounded-lg">{error}</p>
  }
  if (!job) {
    return (
      <div className="flex items-center gap-2 text-gray-400 text-xs p-3">
        <Loader2 size={14} className="animate-spin" /> Starting…
      </div>
    )
  }

  const s = job.last_status
  const icon =
    s === 'ok'      ? <CheckCircle2 size={15} className="text-green-400" /> :
    s === 'warning' ? <AlertTriangle size={15} className="text-amber-400" /> :
    s === 'error'   ? <XCircle size={15} className="text-danger" /> :
                      <Loader2 size={15} className="text-accent animate-spin" />

  return (
    <div className="glass-card p-3">
      <div className="flex items-center gap-2 text-sm text-gray-200">
        {icon}
        <span className="font-medium capitalize">{s ?? 'running'}</span>
        {s === 'running' && <span className="text-gray-500 text-xs">· polling every 2s…</span>}
      </div>
      {s !== 'running' && (
        <div className="text-[11px] text-gray-500 mt-2 space-y-1">
          {job.last_rows != null && <div>Rows: {job.last_rows}</div>}
          {job.last_run_at && <div>Finished: {job.last_run_at.slice(0, 19).replace('T', ' ')}</div>}
          {job.last_error && <div className="text-danger">Error: {job.last_error}</div>}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

Run (from `frontend/`): `npx tsc -b --noEmit`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/automation/RunStatus.tsx
git commit -m "feat(automation): add RunStatus polling component"
```

---

## Task 8: `JobForm.tsx` (the config editor)

**Files:**
- Create: `frontend/src/components/automation/JobForm.tsx`

**Design notes:**
- One `useState<JobConfig>` holds the whole config; typed `Partial<>` patch helpers update each nested section (avoids the computed-key generic pitfall in `.tsx`).
- `headers`/`params` (dicts) and `recipients` (array) are edited as plain text mirrors and serialised on submit (`textToDict` / split-lines).
- Mirrors `components/notes/NoteForm.tsx`: `initial?`, validation, `detail`-message extraction, `onSaved`/`onCancel`, `.input-base`/`.btn-*` classes.

- [ ] **Step 1: Write the component**

Create `frontend/src/components/automation/JobForm.tsx`:

```tsx
import { useState } from 'react'
import { X } from 'lucide-react'
import type {
  AutomationJob, JobConfig, RestSource, RestAuth, RestAuthType,
  ExportSpec, ExportFormat, NotifySpec, EmailSpec,
} from '../../types'
import { createJob, updateJob } from '../../api/automation'

interface Props {
  initial: AutomationJob | null
  onSaved: (job: AutomationJob) => void
  onCancel: () => void
}

const EXPORT_FORMATS: ExportFormat[] = ['duckdb', 'parquet', 'csv', 'xlsx']
const AUTH_TYPES:     RestAuthType[]  = ['none', 'api_key', 'basic', 'bearer']

function blankConfig(): JobConfig {
  return {
    name: '',
    source: {
      url: '', method: 'GET', headers: {}, params: {},
      auth: { type: 'none', header_name: null, value_ref: null, user_ref: null, pass_ref: null },
      records_path: '', pagination: null, timeout_seconds: 30, max_retries: 3,
    },
    shape_sql: '',
    export: { formats: ['duckdb'], dest_dir: '', duckdb_mode: 'overwrite', xlsx_row_guard: 1_000_000 },
    notify: { discord_enabled: false, email: { enabled: false, recipients: [], attach_max_bytes: 10_485_760 } },
  }
}

function dictToText(d: Record<string, string>): string {
  return Object.entries(d).map(([k, v]) => `${k}: ${v}`).join('\n')
}
function textToDict(t: string): Record<string, string> {
  const out: Record<string, string> = {}
  for (const line of t.split('\n')) {
    const i = line.indexOf(':')
    if (i < 0) continue
    const k = line.slice(0, i).trim()
    if (k) out[k] = line.slice(i + 1).trim()
  }
  return out
}

export default function JobForm({ initial, onSaved, onCancel }: Props) {
  const [cfg, setCfg] = useState<JobConfig>(initial?.config ?? blankConfig())
  const [headersText, setHeadersText] = useState(dictToText(initial?.config.source.headers ?? {}))
  const [paramsText,  setParamsText]  = useState(dictToText(initial?.config.source.params ?? {}))
  const [recipText,   setRecipText]   = useState((initial?.config.notify.email.recipients ?? []).join('\n'))
  const [error,  setError]  = useState('')
  const [saving, setSaving] = useState(false)

  const setTop    = (patch: Partial<JobConfig>) => setCfg(c => ({ ...c, ...patch }))
  const setSource = (patch: Partial<RestSource>) => setCfg(c => ({ ...c, source: { ...c.source, ...patch } }))
  const setAuth   = (patch: Partial<RestAuth>)   => setCfg(c => ({ ...c, source: { ...c.source, auth: { ...c.source.auth, ...patch } } }))
  const setExp    = (patch: Partial<ExportSpec>) => setCfg(c => ({ ...c, export: { ...c.export, ...patch } }))
  const setNotify = (patch: Partial<NotifySpec>) => setCfg(c => ({ ...c, notify: { ...c.notify, ...patch } }))
  const setEmail  = (patch: Partial<EmailSpec>)  => setCfg(c => ({ ...c, notify: { ...c.notify, email: { ...c.notify.email, ...patch } } }))

  function toggleFormat(f: ExportFormat) {
    setExp({ formats: cfg.export.formats.includes(f)
      ? cfg.export.formats.filter(x => x !== f)
      : [...cfg.export.formats, f] })
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!cfg.name.trim())                { setError('Job name is required'); return }
    if (!cfg.source.url.trim())          { setError('Source URL is required'); return }
    if (cfg.export.formats.length === 0) { setError('Select at least one export format'); return }
    if (!cfg.export.dest_dir.trim())     { setError('Export destination directory is required'); return }

    const payload: JobConfig = {
      ...cfg,
      name: cfg.name.trim(),
      source: {
        ...cfg.source,
        url: cfg.source.url.trim(),
        headers: textToDict(headersText),
        params: textToDict(paramsText),
        records_path: cfg.source.records_path.trim(),
      },
      export: { ...cfg.export, dest_dir: cfg.export.dest_dir.trim() },
      notify: {
        ...cfg.notify,
        email: { ...cfg.notify.email, recipients: recipText.split('\n').map(s => s.trim()).filter(Boolean) },
      },
    }

    setSaving(true); setError('')
    try {
      const saved = initial ? await updateJob(initial.id, payload) : await createJob(payload)
      onSaved(saved)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Failed to save job')
    } finally {
      setSaving(false)
    }
  }

  const auth = cfg.source.auth
  const pag  = cfg.source.pagination

  return (
    <div className="flex flex-col">
      <div className="px-5 pt-4 pb-3 border-b border-white/5 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white">{initial ? 'Edit Job' : 'New Job'}</h2>
        <button onClick={onCancel} className="text-gray-500 hover:text-white transition-colors"><X size={16} /></button>
      </div>

      <form onSubmit={handleSubmit} className="px-5 py-4 flex flex-col gap-5">
        {/* Name */}
        <div>
          <label className="text-[11px] text-gray-400 mb-1 block">Job Name *</label>
          <input className="input-base text-sm" placeholder="Daily sales pull"
                 value={cfg.name} onChange={e => setTop({ name: e.target.value })} />
        </div>

        {/* ── REST Source ── */}
        <section className="space-y-3">
          <p className="text-[11px] font-semibold text-accent uppercase tracking-wider">REST Source</p>
          <div className="flex gap-3">
            <div className="w-20">
              <label className="text-[11px] text-gray-400 mb-1 block">Method</label>
              <select className="input-base text-sm" value={cfg.source.method} disabled>
                <option value="GET">GET</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="text-[11px] text-gray-400 mb-1 block">URL *</label>
              <input className="input-base text-sm" placeholder="https://api.example.com/v1/items"
                     value={cfg.source.url} onChange={e => setSource({ url: e.target.value })} />
            </div>
          </div>

          <div>
            <label className="text-[11px] text-gray-400 mb-1 block">{'Headers — "Key: Value" per line; use ${VAR} for secrets'}</label>
            <textarea className="input-base text-sm font-mono resize-none min-h-[56px]"
                      placeholder="X-Api-Key: ${API_KEY}" value={headersText}
                      onChange={e => setHeadersText(e.target.value)} />
          </div>

          <div>
            <label className="text-[11px] text-gray-400 mb-1 block">{'Query params — "Key: Value" per line'}</label>
            <textarea className="input-base text-sm font-mono resize-none min-h-[40px]"
                      placeholder="per_page: 100" value={paramsText}
                      onChange={e => setParamsText(e.target.value)} />
          </div>

          {/* Auth */}
          <div>
            <label className="text-[11px] text-gray-400 mb-1 block">Auth</label>
            <select className="input-base text-sm" value={auth.type}
                    onChange={e => setAuth({ type: e.target.value as RestAuthType })}>
              {AUTH_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          {auth.type === 'api_key' && (
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="text-[11px] text-gray-400 mb-1 block">Header Name</label>
                <input className="input-base text-sm" placeholder="X-Api-Key"
                       value={auth.header_name ?? ''} onChange={e => setAuth({ header_name: e.target.value })} />
              </div>
              <div className="flex-1">
                <label className="text-[11px] text-gray-400 mb-1 block">Value env-var name</label>
                <input className="input-base text-sm" placeholder="API_KEY"
                       value={auth.value_ref ?? ''} onChange={e => setAuth({ value_ref: e.target.value })} />
              </div>
            </div>
          )}
          {auth.type === 'bearer' && (
            <div>
              <label className="text-[11px] text-gray-400 mb-1 block">Token env-var name</label>
              <input className="input-base text-sm" placeholder="BEARER_TOKEN"
                     value={auth.value_ref ?? ''} onChange={e => setAuth({ value_ref: e.target.value })} />
            </div>
          )}
          {auth.type === 'basic' && (
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="text-[11px] text-gray-400 mb-1 block">User env-var name</label>
                <input className="input-base text-sm" placeholder="API_USER"
                       value={auth.user_ref ?? ''} onChange={e => setAuth({ user_ref: e.target.value })} />
              </div>
              <div className="flex-1">
                <label className="text-[11px] text-gray-400 mb-1 block">Password env-var name</label>
                <input className="input-base text-sm" placeholder="API_PASS"
                       value={auth.pass_ref ?? ''} onChange={e => setAuth({ pass_ref: e.target.value })} />
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-[11px] text-gray-400 mb-1 block">Records Path</label>
              <input className="input-base text-sm" placeholder="data.items (blank = root array)"
                     value={cfg.source.records_path} onChange={e => setSource({ records_path: e.target.value })} />
            </div>
            <div className="w-24">
              <label className="text-[11px] text-gray-400 mb-1 block">Timeout (s)</label>
              <input type="number" className="input-base text-sm" value={cfg.source.timeout_seconds}
                     onChange={e => setSource({ timeout_seconds: Number(e.target.value) })} />
            </div>
            <div className="w-24">
              <label className="text-[11px] text-gray-400 mb-1 block">Max retries</label>
              <input type="number" className="input-base text-sm" value={cfg.source.max_retries}
                     onChange={e => setSource({ max_retries: Number(e.target.value) })} />
            </div>
          </div>

          {/* Pagination */}
          <label className="flex items-center gap-2 text-xs text-gray-300">
            <input type="checkbox" checked={pag !== null}
                   onChange={e => setSource({ pagination: e.target.checked ? { param: 'page', start: 1 } : null })} />
            Enable pagination
          </label>
          {pag !== null && (
            <div className="flex gap-3 pl-5">
              <div className="flex-1">
                <label className="text-[11px] text-gray-400 mb-1 block">Page param</label>
                <input className="input-base text-sm" value={pag.param}
                       onChange={e => setSource({ pagination: { ...pag, param: e.target.value } })} />
              </div>
              <div className="w-24">
                <label className="text-[11px] text-gray-400 mb-1 block">Start</label>
                <input type="number" className="input-base text-sm" value={pag.start}
                       onChange={e => setSource({ pagination: { ...pag, start: Number(e.target.value) } })} />
              </div>
            </div>
          )}
        </section>

        {/* ── Shaping SQL ── */}
        <section>
          <label className="text-[11px] font-semibold text-accent uppercase tracking-wider mb-1 block">
            {'Shaping SQL — DuckDB over "raw"; blank = passthrough'}
          </label>
          <textarea className="input-base text-sm font-mono resize-none min-h-[80px]"
                    placeholder="SELECT * FROM raw WHERE ..." value={cfg.shape_sql}
                    onChange={e => setTop({ shape_sql: e.target.value })} />
        </section>

        {/* ── Export ── */}
        <section className="space-y-3">
          <p className="text-[11px] font-semibold text-accent uppercase tracking-wider">Export</p>
          <div className="flex gap-3 flex-wrap">
            {EXPORT_FORMATS.map(f => (
              <label key={f} className="flex items-center gap-1.5 text-xs text-gray-300">
                <input type="checkbox" checked={cfg.export.formats.includes(f)} onChange={() => toggleFormat(f)} />
                {f}
              </label>
            ))}
          </div>
          <div>
            <label className="text-[11px] text-gray-400 mb-1 block">Destination directory *</label>
            <input className="input-base text-sm font-mono" placeholder="D:\exports\sales"
                   value={cfg.export.dest_dir} onChange={e => setExp({ dest_dir: e.target.value })} />
          </div>
          {cfg.export.formats.includes('duckdb') && (
            <div className="flex gap-4 items-center">
              <span className="text-[11px] text-gray-400">.duckdb mode:</span>
              {(['overwrite', 'append'] as const).map(m => (
                <label key={m} className="flex items-center gap-1.5 text-xs text-gray-300">
                  <input type="radio" name="duckdb_mode" checked={cfg.export.duckdb_mode === m}
                         onChange={() => setExp({ duckdb_mode: m })} />
                  {m}
                </label>
              ))}
            </div>
          )}
          {cfg.export.formats.includes('xlsx') && (
            <div className="w-40">
              <label className="text-[11px] text-gray-400 mb-1 block">XLSX row guard</label>
              <input type="number" className="input-base text-sm" value={cfg.export.xlsx_row_guard}
                     onChange={e => setExp({ xlsx_row_guard: Number(e.target.value) })} />
            </div>
          )}
        </section>

        {/* ── Notify ── */}
        <section className="space-y-2">
          <p className="text-[11px] font-semibold text-accent uppercase tracking-wider">Notify</p>
          <label className="flex items-center gap-2 text-xs text-gray-300">
            <input type="checkbox" checked={cfg.notify.discord_enabled}
                   onChange={e => setNotify({ discord_enabled: e.target.checked })} />
            Discord (DISCORD_WEBHOOK_URL from .env)
          </label>
          <label className="flex items-center gap-2 text-xs text-gray-300">
            <input type="checkbox" checked={cfg.notify.email.enabled}
                   onChange={e => setEmail({ enabled: e.target.checked })} />
            Email (SMTP_* from .env)
          </label>
          {cfg.notify.email.enabled && (
            <div className="pl-5">
              <label className="text-[11px] text-gray-400 mb-1 block">Recipients (one per line)</label>
              <textarea className="input-base text-sm resize-none min-h-[48px]"
                        placeholder="ops@example.com" value={recipText}
                        onChange={e => setRecipText(e.target.value)} />
            </div>
          )}
        </section>

        {error && (
          <p className="text-danger text-xs bg-danger/10 border border-danger/20 px-3 py-2 rounded-lg">{error}</p>
        )}

        <div className="flex gap-2 pt-1">
          <button type="submit" disabled={saving} className="btn-primary flex-1 text-sm py-2">
            {saving ? 'Saving…' : initial ? 'Save Changes' : 'Create Job'}
          </button>
          <button type="button" onClick={onCancel} className="btn-ghost flex-1 text-sm py-2">Cancel</button>
        </div>
      </form>
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

Run (from `frontend/`): `npx tsc -b --noEmit`
Expected: PASS. (If TS complains about a generic computed-key, confirm the patch helpers use `Partial<…>` exactly as written — that avoids it.)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/automation/JobForm.tsx
git commit -m "feat(automation): add JobForm config editor"
```

---

## Task 9: `Automation.tsx` page (master–detail wiring)

**Files:**
- Create: `frontend/src/pages/data/Automation.tsx`

**Design notes (mirrors `pages/work/QuickNotes.tsx`):**
- Left = `JobList`. Right = action toolbar (only when a **saved** job is selected) + `JobForm` + one result panel.
- `Preview`/`Run`/`Show Code`/`Delete` operate on the **saved** job (`selected.id`) — the backend reads stored config, so the user should **Save before** Preview/Run/Show Code to reflect edits.
- `JobForm` carries `key={selected?.id ?? 'new'}` so switching jobs remounts it with fresh state.
- After Run, `RunStatus` polls and `onDone` refreshes the list + selected job.

- [ ] **Step 1: Write the page**

Create `frontend/src/pages/data/Automation.tsx`:

```tsx
import { useCallback, useEffect, useState } from 'react'
import type { AutomationJob, PreviewResult, JobCode } from '../../types'
import { listJobs, deleteJob, previewJob, runJob, getJobCode } from '../../api/automation'
import JobList from '../../components/automation/JobList'
import JobForm from '../../components/automation/JobForm'
import PreviewPanel from '../../components/automation/PreviewPanel'
import RunStatus from '../../components/automation/RunStatus'
import CodeViewer from '../../components/automation/CodeViewer'

type RightPanel = 'none' | 'preview' | 'run' | 'code'

export default function Automation() {
  const [jobs, setJobs]         = useState<AutomationJob[]>([])
  const [selected, setSelected] = useState<AutomationJob | null>(null)
  const [mode, setMode]         = useState<'empty' | 'form'>('empty')
  const [panel, setPanel]       = useState<RightPanel>('none')
  const [preview, setPreview]   = useState<PreviewResult | null>(null)
  const [code, setCode]         = useState<JobCode | null>(null)
  const [runKey, setRunKey]     = useState(0)
  const [busy, setBusy]         = useState(false)
  const [apiError, setApiError] = useState('')

  const load = useCallback(async () => {
    try { setJobs(await listJobs()); setApiError('') }
    catch { setApiError('Failed to load jobs') }
  }, [])
  useEffect(() => { load() }, [load])

  function resetPanels() { setPanel('none'); setPreview(null); setCode(null) }

  function handleSelect(job: AutomationJob) { setSelected(job); setMode('form'); resetPanels() }
  function handleNew()                       { setSelected(null); setMode('form'); resetPanels() }
  function handleCancel()                    { setSelected(null); setMode('empty'); resetPanels() }

  async function handleSaved(job: AutomationJob) {
    setSelected(job)        // saved → has id → side actions enabled
    setMode('form')
    await load()
  }

  async function handleDelete() {
    if (!selected?.id) return
    if (!window.confirm(`Delete job "${selected.config.name}"?`)) return
    setBusy(true)
    try { await deleteJob(selected.id); setSelected(null); setMode('empty'); resetPanels(); await load() }
    catch { setApiError('Failed to delete job') }
    finally { setBusy(false) }
  }

  async function handlePreview() {
    if (!selected?.id) return
    setBusy(true); setApiError('')
    try { setPreview(await previewJob(selected.id, 100)); setPanel('preview') }
    catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setApiError(typeof detail === 'string' ? detail : 'Preview failed')
    } finally { setBusy(false) }
  }

  async function handleRun() {
    if (!selected?.id) return
    setBusy(true); setApiError('')
    try { await runJob(selected.id); setRunKey(k => k + 1); setPanel('run') }
    catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setApiError(typeof detail === 'string' ? detail : 'Run failed')
    } finally { setBusy(false) }
  }

  async function handleShowCode() {
    if (!selected?.id) return
    setBusy(true); setApiError('')
    try { setCode(await getJobCode(selected.id)); setPanel('code') }
    catch { setApiError('Failed to load code') }
    finally { setBusy(false) }
  }

  async function handleRunDone(job: AutomationJob) {
    setSelected(job)
    await load()
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <JobList jobs={jobs} selectedId={selected?.id ?? null} onSelect={handleSelect} onNew={handleNew} />

      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {mode === 'empty' ? (
          <div className="flex-1 flex items-center justify-center text-gray-600 text-sm">
            Select a job, or click "New" to create one.
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto">
            {selected?.id && (
              <div className="flex items-center gap-2 px-5 pt-4 flex-wrap">
                <button onClick={handlePreview}  disabled={busy} className="btn-ghost text-xs px-3 py-1.5">Preview</button>
                <button onClick={handleRun}      disabled={busy} className="btn-ghost text-xs px-3 py-1.5">Run</button>
                <button onClick={handleShowCode} disabled={busy} className="btn-ghost text-xs px-3 py-1.5">Show Code</button>
                <button onClick={handleDelete}   disabled={busy} className="btn-danger text-xs px-3 py-1.5 ml-auto">Delete</button>
              </div>
            )}
            {apiError && <p className="text-danger text-xs px-5 pt-2">{apiError}</p>}

            <JobForm key={selected?.id ?? 'new'} initial={selected} onSaved={handleSaved} onCancel={handleCancel} />

            {panel !== 'none' && (
              <div className="px-5 pb-6">
                {panel === 'preview' && preview && <PreviewPanel data={preview} />}
                {panel === 'run' && selected?.id && <RunStatus key={runKey} jobId={selected.id} onDone={handleRunDone} />}
                {panel === 'code' && code && (
                  <CodeViewer python={code.python} sql={code.sql} jobName={selected?.config.name ?? 'job'} />
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

Run (from `frontend/`): `npx tsc -b --noEmit`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/data/Automation.tsx
git commit -m "feat(automation): add Automation master-detail page"
```

---

## Task 10: Wire navigation + route

**Files:**
- Modify: `frontend/src/components/layout/Sidebar.tsx` (import `Workflow`, add to `ICON_MAP`, add nav item)
- Modify: `frontend/src/App.tsx` (lazy import + nested route)

> **Note:** Spec §7 writes the route as `/data/automation`, but `App.tsx` uses **relative** child paths under the `AppShell` layout route (e.g. `data/sql`). Use the relative form `data/automation` (no leading slash) to match — a leading slash would break nested routing in react-router-dom v7. The Sidebar `path` keeps the absolute `/data/automation` (NavLink `to` is absolute), consistent with the other nav items.

- [ ] **Step 1: Edit `Sidebar.tsx` — add the icon import**

In the lucide-react import block, add `Workflow`:

```tsx
import {
  LayoutDashboard,
  CheckSquare,
  Hammer,
  BellRing,
  Database,
  Code2,
  Layers,
  TrendingUp,
  BrainCircuit,
  Activity,
  Sparkles,
  NotebookPen,
  ClipboardList,
  Workflow,
} from 'lucide-react'
```

- [ ] **Step 2: Edit `Sidebar.tsx` — register it in `ICON_MAP`**

```tsx
export const ICON_MAP = {
  LayoutDashboard, CheckSquare, Hammer, BellRing,
  Database, Code2, Layers, TrendingUp, BrainCircuit,
  Activity, Sparkles, NotebookPen, ClipboardList, Workflow,
}
```

- [ ] **Step 3: Edit `Sidebar.tsx` — add the nav item to the `data` group**

In the `id: 'data'` category's `items` array, append after the Fabric Views entry:

```tsx
      { path: '/data/fabric',     label: 'Fabric Views',    iconName: 'Layers',   color: '#60a5fa' },
      { path: '/data/automation', label: 'Automation',      iconName: 'Workflow', color: '#60a5fa' },
```

- [ ] **Step 4: Edit `App.tsx` — add the lazy import**

After the existing `FabricViews` lazy import:

```tsx
const FabricViews     = lazy(() => import('./pages/data/FabricViews'))
const Automation      = lazy(() => import('./pages/data/Automation'))
```

- [ ] **Step 5: Edit `App.tsx` — add the route**

After the `data/fabric` route, add (relative path, matching siblings):

```tsx
              <Route path="data/fabric"      element={<FabricViews />} />
              <Route path="data/automation"  element={<Automation />} />
```

- [ ] **Step 6: Type-check**

Run (from `frontend/`): `npx tsc -b --noEmit`
Expected: PASS.

- [ ] **Step 7: Manual smoke (routing only)**

Start the frontend dev server (from `frontend/`): `npm run dev` (serves on port 5177).
In the browser: the sidebar's "SQL SANDBOX" group now shows **Automation** with the workflow icon. Click it → URL becomes `/data/automation`, the page renders with the empty-state message and an "Automation Jobs" panel + "New" button. No console errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/layout/Sidebar.tsx frontend/src/App.tsx
git commit -m "feat(automation): add sidebar nav + route for Automation page"
```

---

## Task 11: End-to-end manual verification

**Files:** none (verification only).

**Prereq:** backend running. From `backend/`: `.venv\Scripts\python.exe -m uvicorn main:app --reload` (serves `/api`). Frontend running from `frontend/`: `npm run dev`.

- [ ] **Step 1: Final type-check / build**

From `frontend/`: `npx tsc -b --noEmit`
Expected: PASS (zero errors across the whole project).
Optionally `npm run build` for a full production typecheck + bundle.

- [ ] **Step 2: Create a job**

Navigate to `/data/automation` → click **New**. Fill:
- Name: `JSONPlaceholder posts`
- URL: `https://jsonplaceholder.typicode.com/posts`
- Records Path: *(blank — response is a root array)*
- Auth: `none`
- Export: check **csv**, Destination directory: a writable temp dir (e.g. `D:\exports\auto_test`)
- Notify: leave both off

Click **Create Job**. Expected: the job appears in the left list with a "never run" badge; the toolbar (Preview/Run/Show Code/Delete) now appears.

- [ ] **Step 3: Preview**

Click **Preview**. Expected: a table renders with columns `userId, id, title, body` and ~100 rows. (If it errors, the message shows inline above the form.)

- [ ] **Step 4: Show Code**

Click **Show Code**. Expected: a panel with **Python** / **SQL** tabs. Python tab shows the generated script (no secret values, only `os.environ[...]` if any); SQL tab shows the shaping SQL (or the passthrough placeholder). "Download .py" / "Download .sql" produce the right extensions.

- [ ] **Step 5: Run + live status**

Click **Run**. Expected: a status panel appears showing "Running · polling every 2s…", then transitions to **ok** with a row count and finish time. The left list's badge updates to `ok` with the row count. A `.csv` file exists in the destination directory.

- [ ] **Step 6: Edit + Delete**

Select the job, change the Name, click **Save Changes** → list label updates. Click **Delete** → confirm → the job disappears and the right panel returns to the empty state.

- [ ] **Step 7: Confirm no regressions**

Open the browser console: no errors during the flow. Visit ML Studio and open a "Python Code" panel there to confirm the `CodePanel` change didn't regress existing Python display.

- [ ] **Step 8: Commit (if any verification tweaks were needed)**

Only if a fix was required during verification — stage the specific changed file(s) and commit. Otherwise nothing to commit.

---

## Self-Review

**Spec coverage (§7):**
- Page `pages/data/Automation.tsx`, 2 columns, JobList + JobForm + Preview/Run/Show Code/Save/Delete buttons → Task 9 (Save/Cancel live in JobForm; Preview/Run/Show Code/Delete in the page toolbar). ✅
- `components/automation/{JobList, JobForm, PreviewPanel, RunStatus}` → Tasks 5, 8, 6, 7. ✅
- Show Code reuses `CodePanel` for Python + SQL tabs → Tasks 3 (generalize `CodePanel`) + 4 (`CodeViewer` wrapper). This honors "reuse CodePanel" while fixing the hardcoded-Python limitation. ✅
- `api/automation.ts` with all 8 fns → Task 2. ✅
- Types in `types.ts` (all 10 named + `JobCode`) → Task 1. ✅
- Sidebar nav (`Workflow` icon, `data` group) → Task 10. ✅
- Route in `App.tsx` → Task 10 (relative path, with the documented leading-slash correction). ✅
- RunStatus polls `GET /jobs/{id}` every ~2s until `!= running` → Task 7. ✅

**API contract (§6.6):** list/get/create/update/delete/preview/run/code paths + verbs match `routers/automation.py`; `preview` body `{n_rows}`; `run` returns `{status}`; `code` returns `{python, sql}`; delete returns `{ok:true}` (ignored). ✅

**Placeholder scan:** every code step contains complete, runnable code — no TBD/TODO/"similar to". ✅

**Type consistency:** `JobConfig`/`RestSource`/`RestAuth`/`ExportSpec`/`NotifySpec`/`EmailSpec`/`Pagination` field names match `models.py`; `PreviewResult = {columns, rows}` matches `runner.preview`; `JobCode = {python, sql}` matches `/code`; component prop names (`onSaved/onCancel/onSelect/onNew/onDone/initial/data/jobId`) are consistent between definition and call sites in Task 9. ✅

**Adaptation note:** "TDD failing test" steps are replaced by `npx tsc -b --noEmit` because the frontend has no test runner; behavioural verification is consolidated into Tasks 10–11. This is intentional and matches the existing repo (frontend ships without Vitest/Jest).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-05-automation-frontend.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, two-stage review (spec compliance, then code quality) between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session via executing-plans, batch execution with checkpoints.
