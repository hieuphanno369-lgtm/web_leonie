import { useState } from 'react'
import { Check, X } from 'lucide-react'
import type { Task, TaskStatus, TaskType } from '../../types'
import type { TaskPayload } from '../../api/tasks'
import { MSG } from '../../messages'

interface Props {
  initial?: Task          // undefined → create mode
  onSave: (payload: TaskPayload) => Promise<void>
  onCancel: () => void
}

export default function TaskForm({ initial, onSave, onCancel }: Props) {
  const [type,      setType]      = useState<TaskType>(initial?.type      ?? 'task')
  const [title,     setTitle]     = useState(initial?.title     ?? '')
  const [status,    setStatus]    = useState<TaskStatus>(initial?.status   ?? 'todo')
  const [priority,  setPriority]  = useState<Task['priority']>(initial?.priority ?? 'medium')
  const [dueDate,   setDueDate]   = useState(initial?.due_date  ?? '')
  const [recurring, setRecurring] = useState(initial?.recurring ?? '')
  const [notes,     setNotes]     = useState(initial?.notes     ?? '')
  const [requester, setRequester] = useState(initial?.requester ?? '')
  const [dataset,   setDataset]   = useState(initial?.dataset   ?? '')
  const [error,     setError]     = useState('')
  const [saving,    setSaving]    = useState(false)

  async function handleSubmit() {
    if (!title.trim()) { setError(MSG.titleRequired); return }
    if (type === 'eda' && !requester.trim()) { setError(MSG.requesterRequiredEda); return }
    if (type === 'eda' && !dataset.trim())   { setError(MSG.datasetRequiredEda); return }
    setError('')
    setSaving(true)
    try {
      await onSave({
        title:     title.trim(),
        type,
        status,
        priority,
        due_date:  dueDate   || null,
        recurring: type === 'task' ? ((recurring as 'daily' | 'weekly') || null) : null,
        notes:     notes     || null,
        requester: type === 'eda' ? (requester.trim() || null) : null,
        dataset:   type === 'eda' ? (dataset.trim()   || null) : null,
      })
    } catch {
      setError(MSG.saveFailed)
    } finally {
      setSaving(false)
    }
  }

  const isEda = type === 'eda'

  return (
    <div className="flex-1 p-5 overflow-y-auto">
      <h2 className="text-sm font-semibold text-white mb-4">
        {initial ? '✏️ Edit' : '＋ New'} {isEda ? 'EDA Request' : 'Task'}
      </h2>

      {/* Type toggle */}
      {!initial && (
        <div className="flex gap-2 mb-4">
          {(['task', 'eda'] as TaskType[]).map(t => (
            <button
              key={t}
              onClick={() => setType(t)}
              className={`px-3 py-1 rounded text-xs border transition-all ${
                type === t
                  ? 'bg-work/10 text-work border-work/30'
                  : 'text-gray-500 border-white/10 hover:text-gray-300'
              }`}
            >
              {t === 'task' ? '☐ Task' : '🔬 EDA Request'}
            </button>
          ))}
        </div>
      )}

      {/* Title */}
      <div className="mb-3">
        <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">
          Title *
        </label>
        <input
          className="input-base"
          placeholder={isEda ? 'Cần phân tích gì?' : 'Cần làm gì?'}
          value={title}
          onChange={e => setTitle(e.target.value)}
          autoFocus
        />
      </div>

      {/* EDA-specific fields */}
      {isEda && (
        <div className="flex gap-3 mb-3">
          <div className="flex-1">
            <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">
              Requester *
            </label>
            <input
              className="input-base"
              placeholder="Ai yêu cầu?"
              value={requester}
              onChange={e => setRequester(e.target.value)}
            />
          </div>
          <div className="flex-1">
            <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">
              Dataset *
            </label>
            <input
              className="input-base"
              placeholder="Nguồn dữ liệu / bảng"
              value={dataset}
              onChange={e => setDataset(e.target.value)}
            />
          </div>
        </div>
      )}

      {/* Status + Priority */}
      <div className="flex gap-3 mb-3">
        <div className="flex-1">
          <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Status</label>
          <select className="input-base" value={status} onChange={e => setStatus(e.target.value as TaskStatus)}>
            <option value="todo">Todo</option>
            <option value="in_progress">In Progress</option>
            <option value="done">Done</option>
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Priority</label>
          <select className="input-base" value={priority} onChange={e => setPriority(e.target.value as Task['priority'])}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
      </div>

      {/* Due date + Recurring (recurring only for regular tasks) */}
      <div className="flex gap-3 mb-3">
        <div className="flex-1">
          <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Due date</label>
          <input
            type="date"
            className="input-base"
            value={dueDate}
            onChange={e => setDueDate(e.target.value)}
          />
        </div>
        {!isEda && (
          <div className="flex-1">
            <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Recurring</label>
            <select className="input-base" value={recurring} onChange={e => setRecurring(e.target.value)}>
              <option value="">None</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
            </select>
          </div>
        )}
      </div>

      {/* Notes */}
      <div className="mb-4">
        <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Notes</label>
        <textarea
          className="input-base resize-none"
          rows={4}
          placeholder="Ghi chú (không bắt buộc)..."
          value={notes}
          onChange={e => setNotes(e.target.value)}
        />
      </div>

      {error && <p className="text-danger text-xs mb-3">{error}</p>}

      <button
        onClick={handleSubmit}
        disabled={saving}
        className="btn-primary w-full mb-2 flex items-center justify-center gap-1.5 disabled:opacity-50"
      >
        <Check size={13} /> {saving ? 'Saving...' : `Save ${isEda ? 'EDA Request' : 'Task'}`}
      </button>
      <button onClick={onCancel} className="btn-ghost w-full flex items-center justify-center gap-1.5">
        <X size={13} /> Cancel
      </button>
    </div>
  )
}
