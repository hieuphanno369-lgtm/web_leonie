import { useState } from 'react'
import { X } from 'lucide-react'
import type {
  AutomationJob, JobConfig, RestSource, RestAuth, RestAuthType,
  SalesforceSource, SourceType,
  ExportSpec, ExportFormat, NotifySpec, EmailSpec,
} from '../../types'
import { createJob, updateJob, verifyPath } from '../../api/automation'
import { MSG } from '../../messages'

interface Props {
  initial: AutomationJob | null
  onSaved: (job: AutomationJob) => void
  onCancel: () => void
}

const EXPORT_FORMATS: ExportFormat[] = ['duckdb', 'parquet', 'csv', 'xlsx']
const AUTH_TYPES:     RestAuthType[]  = ['none', 'api_key', 'basic', 'bearer']

function blankRestSource(): RestSource {
  return {
    source_type: 'rest',
    url: '', method: 'GET', headers: {}, params: {},
    auth: { type: 'none', header_name: null, value_ref: null, user_ref: null, pass_ref: null },
    records_path: '', pagination: null, timeout_seconds: 30, max_retries: 3,
  }
}

function blankSfSource(): SalesforceSource {
  return {
    source_type: 'salesforce',
    soql: '', object_name: '', use_bulk: true,
    user_ref: 'SF_User', pass_ref: 'SF_Password',
    token_ref: '', instance_url: 'https://your-org.my.salesforce.com',
  }
}

function blankConfig(): JobConfig {
  return {
    name: '',
    source: blankRestSource(),
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
  const initCfg = initial?.config ?? blankConfig()
  const [cfg, setCfg] = useState<JobConfig>(initCfg)
  const [sourceType, setSourceType] = useState<SourceType>(
    (initCfg.source.source_type as SourceType) ?? 'rest'
  )

  const restSource = cfg.source.source_type === 'rest' ? cfg.source : blankRestSource()
  const sfSource   = cfg.source.source_type === 'salesforce' ? cfg.source : blankSfSource()

  const [headersText, setHeadersText] = useState(dictToText(restSource.headers ?? {}))
  const [paramsText,  setParamsText]  = useState(dictToText(restSource.params ?? {}))
  const [recipText,   setRecipText]   = useState((initCfg.notify.email.recipients ?? []).join('\n'))
  const [error,  setError]  = useState('')
  const [saving, setSaving] = useState(false)
  const [pathCheck, setPathCheck] = useState<{ ok: boolean; msg: string } | null>(null)
  const [checking,  setChecking]  = useState(false)

  const setTop    = (patch: Partial<JobConfig>) => setCfg(c => ({ ...c, ...patch }))
  const setRest   = (patch: Partial<RestSource>) =>
    setCfg(c => ({ ...c, source: { ...(c.source as RestSource), ...patch } }))
  const setAuth   = (patch: Partial<RestAuth>) =>
    setCfg(c => ({ ...c, source: { ...(c.source as RestSource), auth: { ...(c.source as RestSource).auth, ...patch } } }))
  const setSf     = (patch: Partial<SalesforceSource>) =>
    setCfg(c => ({ ...c, source: { ...(c.source as SalesforceSource), ...patch } }))
  const setExp    = (patch: Partial<ExportSpec>) => setCfg(c => ({ ...c, export: { ...c.export, ...patch } }))
  const setNotify = (patch: Partial<NotifySpec>) => setCfg(c => ({ ...c, notify: { ...c.notify, ...patch } }))
  const setEmail  = (patch: Partial<EmailSpec>)  =>
    setCfg(c => ({ ...c, notify: { ...c.notify, email: { ...c.notify.email, ...patch } } }))

  function switchSourceType(t: SourceType) {
    setSourceType(t)
    setCfg(c => ({ ...c, source: t === 'salesforce' ? blankSfSource() : blankRestSource() }))
  }

  function toggleFormat(f: ExportFormat) {
    setExp({ formats: cfg.export.formats.includes(f)
      ? cfg.export.formats.filter(x => x !== f)
      : [...cfg.export.formats, f] })
  }

  async function verifyDest() {
    const dir = cfg.export.dest_dir.trim()
    if (!dir) { setPathCheck({ ok: false, msg: MSG.enterDirFirst }); return }
    setChecking(true)
    try {
      const r = await verifyPath(dir)
      setPathCheck({ ok: r.ok, msg: r.message })
    } catch {
      setPathCheck({ ok: false, msg: MSG.verifyPathFailed })
    } finally {
      setChecking(false)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!cfg.name.trim()) { setError(MSG.jobNameRequired); return }
    if (cfg.export.formats.length === 0) { setError(MSG.exportFormatRequired); return }
    if (!cfg.export.dest_dir.trim())     { setError(MSG.exportDirRequired); return }

    let source: JobConfig['source']
    if (sourceType === 'salesforce') {
      const s = cfg.source as SalesforceSource
      if (!s.soql.trim())       { setError(MSG.soqlRequired); return }
      if (!s.object_name.trim()) { setError(MSG.objectNameRequired); return }
      source = { ...s, soql: s.soql.trim(), object_name: s.object_name.trim() }
    } else {
      const s = cfg.source as RestSource
      if (!s.url.trim()) { setError(MSG.sourceUrlRequired); return }
      source = {
        ...s,
        url: s.url.trim(),
        headers: textToDict(headersText),
        params: textToDict(paramsText),
        records_path: s.records_path.trim(),
      }
    }

    const payload: JobConfig = {
      ...cfg,
      name: cfg.name.trim(),
      source,
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
      setError(typeof detail === 'string' ? detail : MSG.saveJobFailed)
    } finally {
      setSaving(false)
    }
  }

  const auth = (cfg.source as RestSource).auth ?? { type: 'none' }
  const pag  = (cfg.source as RestSource).pagination ?? null

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

        {/* ── Source type tabs ── */}
        <section className="space-y-3">
          <div className="flex gap-1 p-0.5 bg-white/5 rounded-lg w-fit">
            {(['rest', 'salesforce'] as SourceType[]).map(t => (
              <button key={t} type="button"
                      className={`px-3 py-1 text-xs rounded-md transition-colors ${
                        sourceType === t ? 'bg-accent text-black font-semibold' : 'text-gray-400 hover:text-white'
                      }`}
                      onClick={() => switchSourceType(t)}>
                {t === 'rest' ? 'REST API' : 'Salesforce'}
              </button>
            ))}
          </div>

          {/* ── REST fields ── */}
          {sourceType === 'rest' && (<>
            <div className="flex gap-3">
              <div className="w-20">
                <label className="text-[11px] text-gray-400 mb-1 block">Method</label>
                <select className="input-base text-sm" value="GET" disabled>
                  <option value="GET">GET</option>
                </select>
              </div>
              <div className="flex-1">
                <label className="text-[11px] text-gray-400 mb-1 block">URL *</label>
                <input className="input-base text-sm" placeholder="https://api.example.com/v1/items"
                       value={(cfg.source as RestSource).url ?? ''}
                       onChange={e => setRest({ url: e.target.value })} />
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
                       value={(cfg.source as RestSource).records_path ?? ''}
                       onChange={e => setRest({ records_path: e.target.value })} />
              </div>
              <div className="w-24">
                <label className="text-[11px] text-gray-400 mb-1 block">Timeout (s)</label>
                <input type="number" className="input-base text-sm"
                       value={(cfg.source as RestSource).timeout_seconds ?? 30}
                       onChange={e => setRest({ timeout_seconds: Number(e.target.value) })} />
              </div>
              <div className="w-24">
                <label className="text-[11px] text-gray-400 mb-1 block">Max retries</label>
                <input type="number" className="input-base text-sm"
                       value={(cfg.source as RestSource).max_retries ?? 3}
                       onChange={e => setRest({ max_retries: Number(e.target.value) })} />
              </div>
            </div>

            <label className="flex items-center gap-2 text-xs text-gray-300">
              <input type="checkbox" checked={pag !== null}
                     onChange={e => setRest({ pagination: e.target.checked ? { param: 'page', start: 1 } : null })} />
              Enable pagination
            </label>
            {pag !== null && (
              <div className="flex gap-3 pl-5">
                <div className="flex-1">
                  <label className="text-[11px] text-gray-400 mb-1 block">Page param</label>
                  <input className="input-base text-sm" value={pag.param}
                         onChange={e => setRest({ pagination: { ...pag, param: e.target.value } })} />
                </div>
                <div className="w-24">
                  <label className="text-[11px] text-gray-400 mb-1 block">Start</label>
                  <input type="number" className="input-base text-sm" value={pag.start}
                         onChange={e => setRest({ pagination: { ...pag, start: Number(e.target.value) } })} />
                </div>
              </div>
            )}
          </>)}

          {/* ── Salesforce fields ── */}
          {sourceType === 'salesforce' && (<>
            <div>
              <label className="text-[11px] text-gray-400 mb-1 block">Object Name *</label>
              <input className="input-base text-sm font-mono" placeholder="Transaction__c"
                     value={sfSource.object_name}
                     onChange={e => setSf({ object_name: e.target.value })} />
            </div>

            <div>
              <label className="text-[11px] text-gray-400 mb-1 block">SOQL Query *</label>
              <textarea className="input-base text-sm font-mono resize-none min-h-[100px]"
                        placeholder={"SELECT Id, Name FROM Transaction__c\nWHERE Transaction_Date__c >= 2026-01-01"}
                        value={sfSource.soql}
                        onChange={e => setSf({ soql: e.target.value })} />
            </div>

            <label className="flex items-center gap-2 text-xs text-gray-300">
              <input type="checkbox" checked={sfSource.use_bulk}
                     onChange={e => setSf({ use_bulk: e.target.checked })} />
              Use Bulk API (recommended for large tables — uses bulk2)
            </label>

            <p className="text-[11px] font-semibold text-accent uppercase tracking-wider pt-1">Credentials (env var names)</p>
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="text-[11px] text-gray-400 mb-1 block">Username env-var</label>
                <input className="input-base text-sm font-mono" placeholder="SF_User"
                       value={sfSource.user_ref}
                       onChange={e => setSf({ user_ref: e.target.value })} />
              </div>
              <div className="flex-1">
                <label className="text-[11px] text-gray-400 mb-1 block">Password env-var</label>
                <input className="input-base text-sm font-mono" placeholder="SF_Password"
                       value={sfSource.pass_ref}
                       onChange={e => setSf({ pass_ref: e.target.value })} />
              </div>
            </div>
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="text-[11px] text-gray-400 mb-1 block">Security token env-var (blank = no token)</label>
                <input className="input-base text-sm font-mono" placeholder="SF_Token"
                       value={sfSource.token_ref}
                       onChange={e => setSf({ token_ref: e.target.value })} />
              </div>
              <div className="flex-1">
                <label className="text-[11px] text-gray-400 mb-1 block">Instance URL</label>
                <input className="input-base text-sm font-mono"
                       placeholder="https://your-org.my.salesforce.com"
                       value={sfSource.instance_url}
                       onChange={e => setSf({ instance_url: e.target.value })} />
              </div>
            </div>
          </>)}
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
            <div className="flex gap-2">
              <input className="input-base text-sm font-mono flex-1" placeholder="D:\exports\sales"
                     value={cfg.export.dest_dir}
                     onChange={e => { setExp({ dest_dir: e.target.value }); setPathCheck(null) }} />
              <button type="button" onClick={verifyDest} disabled={checking}
                      className="btn-ghost text-xs px-3 whitespace-nowrap">
                {checking ? 'Checking…' : 'Verify path'}
              </button>
            </div>
            {pathCheck && (
              <p className={`text-[11px] mt-1 ${pathCheck.ok ? 'text-emerald-400' : 'text-danger'}`}>
                {pathCheck.ok ? '✓ ' : '✗ '}{pathCheck.msg}
              </p>
            )}
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
