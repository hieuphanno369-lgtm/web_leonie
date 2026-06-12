import { useState } from 'react'
import { X } from 'lucide-react'
import type { QuickNote, Task, EDARequest } from '../../types'
import { createNote, updateNote } from '../../api/notes'
import type { NotePayload } from '../../api/notes'
import { MSG } from '../../messages'

interface Props {
  initial?: QuickNote | null
  tasks: Task[]
  edas: EDARequest[]
  onSaved: (note: QuickNote) => void
  onCancel: () => void
}

const CATEGORIES = ['daily', 'meeting', 'idea', 'bug']

export default function NoteForm({ initial, tasks, edas, onSaved, onCancel }: Props) {
  const today = new Date().toISOString().slice(0, 10)

  const [title,    setTitle]    = useState(initial?.title    ?? '')
  const [content,  setContent]  = useState(initial?.content  ?? '')
  const [date,     setDate]     = useState(initial?.date     ?? today)
  const [category, setCategory] = useState(initial?.category ?? '')
  const [taskId,   setTaskId]   = useState(initial?.task_id  ?? '')
  const [edaId,    setEdaId]    = useState(initial?.eda_id   ?? '')
  const [error,    setError]    = useState('')
  const [saving,   setSaving]   = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!content.trim()) { setError(MSG.contentRequired); return }
    if (!date)           { setError(MSG.dateRequired);    return }

    const payload: NotePayload = {
      title:    title.trim()    || null,
      content:  content.trim(),
      date,
      category: category.trim() || null,
      task_id:  taskId          || null,
      eda_id:   edaId           || null,
    }

    setSaving(true)
    setError('')
    try {
      const saved = initial
        ? await updateNote(initial.id, payload)
        : await createNote(payload)
      onSaved(saved)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? MSG.saveNoteFailed
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="px-5 pt-4 pb-3 border-b border-white/5 flex items-center justify-between flex-shrink-0">
        <h2 className="text-sm font-semibold text-white">
          {initial ? 'Edit Note' : 'New Note'}
        </h2>
        <button onClick={onCancel} className="text-gray-500 hover:text-white transition-colors">
          <X size={16} />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="flex-1 flex flex-col px-5 py-4 gap-4">
        {/* Title */}
        <div>
          <label className="text-[11px] text-gray-400 mb-1 block">Title (optional)</label>
          <input
            className="input-base text-sm w-full"
            placeholder="Tiêu đề ngắn..."
            value={title}
            onChange={e => setTitle(e.target.value)}
          />
        </div>

        {/* Content */}
        <div className="flex-1 flex flex-col">
          <label className="text-[11px] text-gray-400 mb-1 block">Content *</label>
          <textarea
            className="input-base text-sm w-full flex-1 resize-none min-h-[140px]"
            placeholder="Viết ghi chú của bạn..."
            value={content}
            onChange={e => setContent(e.target.value)}
          />
        </div>

        {/* Date + Category row */}
        <div className="flex gap-3">
          <div className="flex-1">
            <label className="text-[11px] text-gray-400 mb-1 block">Date *</label>
            <input
              type="date"
              className="input-base text-sm w-full"
              value={date}
              onChange={e => setDate(e.target.value)}
            />
          </div>
          <div className="flex-1">
            <label className="text-[11px] text-gray-400 mb-1 block">Category</label>
            <select
              className="input-base text-sm w-full"
              value={category}
              onChange={e => setCategory(e.target.value)}
            >
              <option value="">None</option>
              {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        </div>

        {/* Link to Task */}
        <div>
          <label className="text-[11px] text-gray-400 mb-1 block">Link to Task (optional)</label>
          <select
            className="input-base text-sm w-full"
            value={taskId}
            onChange={e => { setTaskId(e.target.value); if (e.target.value) setEdaId('') }}
          >
            <option value="">None</option>
            {tasks.map(t => (
              <option key={t.id} value={t.id}>{t.title}</option>
            ))}
          </select>
        </div>

        {/* Link to EDA */}
        <div>
          <label className="text-[11px] text-gray-400 mb-1 block">Link to EDA Request (optional)</label>
          <select
            className="input-base text-sm w-full"
            value={edaId}
            onChange={e => { setEdaId(e.target.value); if (e.target.value) setTaskId('') }}
          >
            <option value="">None</option>
            {edas.map(eda => (
              <option key={eda.id} value={eda.id}>{eda.title}</option>
            ))}
          </select>
        </div>

        {/* Error */}
        {error && (
          <p className="text-danger text-xs bg-danger/10 border border-danger/20 px-3 py-2 rounded-lg">
            {error}
          </p>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-1">
          <button type="submit" disabled={saving} className="btn-primary flex-1 text-sm py-2">
            {saving ? 'Saving…' : initial ? 'Save Changes' : 'Create Note'}
          </button>
          <button type="button" onClick={onCancel} className="btn-ghost flex-1 text-sm py-2">
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
