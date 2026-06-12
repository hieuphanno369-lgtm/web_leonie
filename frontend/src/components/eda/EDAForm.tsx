import { useState } from 'react'
import { Check, X } from 'lucide-react'
import type { EDARequest, EDAStatus, EDAPriority } from '../../types'
import type { EDAPayload } from '../../api/eda'
import { MSG } from '../../messages'

interface Props {
  initial?: EDARequest
  onSave: (payload: EDAPayload) => Promise<void>
  onCancel: () => void
}

export default function EDAForm({ initial, onSave, onCancel }: Props) {
  const [title,     setTitle]     = useState(initial?.title     ?? '')
  const [requester, setRequester] = useState(initial?.requester ?? '')
  const [dataset,   setDataset]   = useState(initial?.dataset   ?? '')
  const [status,    setStatus]    = useState<EDAStatus>(initial?.status   ?? 'todo')
  const [priority,  setPriority]  = useState<EDAPriority>(initial?.priority ?? 'medium')
  const [dueDate,   setDueDate]   = useState(initial?.due_date  ?? '')
  const [notes,     setNotes]     = useState(initial?.notes     ?? '')
  const [error,     setError]     = useState('')
  const [saving,    setSaving]    = useState(false)

  async function handleSubmit() {
    if (!title.trim())     { setError(MSG.titleRequired);     return }
    if (!requester.trim()) { setError(MSG.requesterRequired); return }
    if (!dataset.trim())   { setError(MSG.datasetRequired);   return }
    setError('')
    setSaving(true)
    try {
      await onSave({
        title: title.trim(),
        requester: requester.trim(),
        dataset: dataset.trim(),
        status,
        priority,
        due_date: dueDate || null,
        notes: notes || null,
      })
    } catch {
      setError(MSG.saveFailed)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex-1 p-5 overflow-y-auto">
      <h2 className="text-sm font-semibold text-white mb-4">
        {initial ? '✏️ Edit EDA Request' : '＋ New EDA Request'}
      </h2>

      <div className="mb-3">
        <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Title *</label>
        <input className="input-base" placeholder="EDA ColosBaby T04..." value={title} onChange={e => setTitle(e.target.value)} autoFocus />
      </div>

      <div className="flex gap-3 mb-3">
        <div className="flex-1">
          <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Requester *</label>
          <input className="input-base" placeholder="Nguyen Van A" value={requester} onChange={e => setRequester(e.target.value)} />
        </div>
        <div className="flex-1">
          <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Dataset *</label>
          <input className="input-base" placeholder="SF_ColosBaby_2024" value={dataset} onChange={e => setDataset(e.target.value)} />
        </div>
      </div>

      <div className="flex gap-3 mb-3">
        <div className="flex-1">
          <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Status</label>
          <select className="input-base" value={status} onChange={e => setStatus(e.target.value as EDAStatus)}>
            <option value="todo">Todo</option>
            <option value="in_progress">In Progress</option>
            <option value="done">Done</option>
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Priority</label>
          <select className="input-base" value={priority} onChange={e => setPriority(e.target.value as EDAPriority)}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
      </div>

      <div className="mb-3">
        <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Due date</label>
        <input type="date" className="input-base" value={dueDate} onChange={e => setDueDate(e.target.value)} />
      </div>

      <div className="mb-4">
        <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Notes</label>
        <textarea className="input-base resize-none" rows={3} placeholder="Ghi chú (không bắt buộc)..." value={notes} onChange={e => setNotes(e.target.value)} />
      </div>

      {error && <p className="text-danger text-xs mb-3">{error}</p>}

      <button onClick={handleSubmit} disabled={saving} className="btn-primary w-full mb-2 flex items-center justify-center gap-1.5 disabled:opacity-50">
        <Check size={13} /> {saving ? 'Saving...' : 'Save Request'}
      </button>
      <button onClick={onCancel} className="btn-ghost w-full flex items-center justify-center gap-1.5">
        <X size={13} /> Cancel
      </button>
    </div>
  )
}
