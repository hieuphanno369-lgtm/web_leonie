import { useState, useEffect } from 'react'
import { Pencil, Trash2 } from 'lucide-react'
import type { Task } from '../../types'

interface Props {
  task: Task
  onEdit: () => void
  onDelete: (id: string) => void
}

export default function TaskDetail({ task, onEdit, onDelete }: Props) {
  const [confirmDelete, setConfirmDelete] = useState(false)

  useEffect(() => {
    setConfirmDelete(false)
  }, [task.id])

  const statusCls: Record<string, string> = {
    todo:        'bg-warning/10 text-warning border-warning/25',
    in_progress: 'bg-data/10 text-data border-data/25',
    done:        'bg-work/10 text-work border-work/25',
  }
  const priorityCls: Record<string, string> = {
    high:   'bg-danger/10 text-danger border-danger/25',
    medium: 'bg-data/10 text-data border-data/25',
    low:    'bg-white/5 text-gray-500 border-white/10',
  }

  const fmtDate = (iso: string) =>
    new Date(iso).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })

  return (
    <div className="flex-1 p-5 overflow-y-auto">
      {/* Title + actions */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <h2 className="text-base font-semibold text-white leading-snug">{task.title}</h2>
        <div className="flex gap-2 flex-shrink-0">
          <button onClick={onEdit} className="btn-ghost flex items-center gap-1 text-xs px-2.5 py-1">
            <Pencil size={12} /> Edit
          </button>
          {confirmDelete ? (
            <button
              onClick={() => onDelete(task.id)}
              className="btn-danger flex items-center gap-1 text-xs px-2.5 py-1"
            >
              <Trash2 size={12} /> Confirm
            </button>
          ) : (
            <button
              onClick={() => setConfirmDelete(true)}
              className="btn-ghost flex items-center gap-1 text-xs px-2.5 py-1 hover:text-danger hover:border-danger/30"
            >
              <Trash2 size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Chips */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {task.type === 'eda' && (
          <span className="badge bg-analytics/10 text-analytics border border-analytics/25">
            🔬 EDA
          </span>
        )}
        <span className={`badge border ${statusCls[task.status]}`}>
          {task.status.replace('_', ' ')}
        </span>
        <span className={`badge border ${priorityCls[task.priority]}`}>
          {task.priority} priority
        </span>
        {task.due_date && (
          <span className="badge bg-white/5 text-gray-400 border border-white/10">
            📅 {fmtDate(task.due_date)}
          </span>
        )}
        {task.recurring && (
          <span className="badge bg-learn/10 text-learn border border-learn/25">
            🔁 {task.recurring}
          </span>
        )}
      </div>

      <hr className="border-white/5 mb-4" />

      {/* EDA-specific fields */}
      {task.type === 'eda' && (task.requester || task.dataset) && (
        <div className="mb-4 grid grid-cols-2 gap-3">
          {task.requester && (
            <div>
              <p className="text-[10px] uppercase tracking-widest text-gray-600 mb-1">Requester</p>
              <p className="text-xs text-gray-300">{task.requester}</p>
            </div>
          )}
          {task.dataset && (
            <div>
              <p className="text-[10px] uppercase tracking-widest text-gray-600 mb-1">Dataset</p>
              <p className="text-xs text-gray-300">{task.dataset}</p>
            </div>
          )}
        </div>
      )}

      {/* Notes */}
      <div className="mb-4">
        <p className="text-[10px] uppercase tracking-widest text-gray-600 mb-2">Notes</p>
        <div className="bg-secondary border border-white/5 rounded-lg px-3 py-2.5 text-xs text-gray-400 leading-relaxed min-h-[72px] whitespace-pre-wrap">
          {task.notes ?? <span className="italic text-gray-600">No notes</span>}
        </div>
      </div>

      {/* Meta */}
      <div>
        <p className="text-[10px] uppercase tracking-widest text-gray-600 mb-2">Info</p>
        <p className="text-xs text-gray-500 mb-1">Created: <span className="text-gray-400">{fmtDate(task.created)}</span></p>
        <p className="text-xs text-gray-500">Updated: <span className="text-gray-400">{fmtDate(task.updated)}</span></p>
      </div>
    </div>
  )
}
