import { Plus } from 'lucide-react'
import type { AutomationJob } from '../../types'
import { useResizableSidebar, ResizeHandle } from '../layout/ResizableSidebar'
import { MSG } from '../../messages'

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
  const { width, onDragStart } = useResizableSidebar({
    initial: 288, min: 220, max: 520, storageKey: 'leonie:job-sidebar-w',
  })
  return (
    <>
    <div style={{ width }} className="flex-shrink-0 border-r border-white/5 flex flex-col h-full">
      <div className="px-4 pt-4 pb-3 border-b border-white/5 flex items-center justify-between flex-shrink-0">
        <h2 className="text-sm font-semibold text-white">Automation Jobs</h2>
        <button onClick={onNew} className="btn-primary text-xs px-2 py-1 flex items-center gap-1">
          <Plus size={13} /> New
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {jobs.length === 0 && (
          <p className="text-gray-600 text-xs text-center mt-8">{MSG.emptyJobList}</p>
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
    <ResizeHandle onDragStart={onDragStart} color="data" />
    </>
  )
}
