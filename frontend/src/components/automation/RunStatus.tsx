import { useEffect, useRef, useState } from 'react'
import { Loader2, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react'
import type { AutomationJob } from '../../types'
import { getJob } from '../../api/automation'
import { MSG } from '../../messages'

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
        setError(typeof detail === 'string' ? detail : MSG.pollStatusFailed)
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
