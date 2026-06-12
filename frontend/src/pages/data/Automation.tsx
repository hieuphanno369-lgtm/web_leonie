import { useCallback, useEffect, useState } from 'react'
import type { AutomationJob, PreviewResult, JobCode } from '../../types'
import { listJobs, deleteJob, previewJob, runJob, getJobCode } from '../../api/automation'
import JobList from '../../components/automation/JobList'
import JobForm from '../../components/automation/JobForm'
import PreviewPanel from '../../components/automation/PreviewPanel'
import RunStatus from '../../components/automation/RunStatus'
import CodeViewer from '../../components/automation/CodeViewer'
import { MSG } from '../../messages'

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
    catch { setApiError(MSG.loadJobsFailed) }
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
    if (!window.confirm(MSG.confirmDelete(`công việc "${selected.config.name}"`))) return
    setBusy(true)
    try { await deleteJob(selected.id); setSelected(null); setMode('empty'); resetPanels(); await load() }
    catch { setApiError(MSG.deleteJobFailed) }
    finally { setBusy(false) }
  }

  async function handlePreview() {
    if (!selected?.id) return
    setBusy(true); setApiError('')
    try { setPreview(await previewJob(selected.id, 100)); setPanel('preview') }
    catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setApiError(typeof detail === 'string' ? detail : MSG.previewFailed)
    } finally { setBusy(false) }
  }

  async function handleRun() {
    if (!selected?.id) return
    setBusy(true); setApiError('')
    try { await runJob(selected.id); setRunKey(k => k + 1); setPanel('run') }
    catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setApiError(typeof detail === 'string' ? detail : MSG.runFailed)
    } finally { setBusy(false) }
  }

  async function handleShowCode() {
    if (!selected?.id) return
    setBusy(true); setApiError('')
    try { setCode(await getJobCode(selected.id)); setPanel('code') }
    catch { setApiError(MSG.loadCodeFailed) }
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
            {MSG.emptySelectJob}
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
