import { useState } from 'react'
import { Check, X } from 'lucide-react'
import type { ActionPlan, APCategory, APStatus, APPriority } from '../../types'
import type { APPayload } from '../../api/action_plan'
import { MSG } from '../../messages'

interface Props {
  initial?: ActionPlan
  onSave: (payload: APPayload) => Promise<void>
  onCancel: () => void
}

export default function APForm({ initial, onSave, onCancel }: Props) {
  const [title,      setTitle]      = useState(initial?.title       ?? '')
  const [category,   setCategory]   = useState<APCategory>(initial?.category   ?? 'other')
  const [status,     setStatus]     = useState<APStatus>(initial?.status     ?? 'draft')
  const [priority,   setPriority]   = useState<APPriority>(initial?.priority   ?? 'medium')
  const [problem,    setProblem]    = useState(initial?.problem     ?? '')
  const [picMain,    setPicMain]    = useState(initial?.pic_main    ?? '')
  const [picSupport, setPicSupport] = useState(initial?.pic_support ?? '')
  const [dueDate,    setDueDate]    = useState(initial?.due_date    ?? '')
  const [error,      setError]      = useState('')
  const [saving,     setSaving]     = useState(false)

  async function handleSubmit() {
    if (!title.trim()) { setError(MSG.titleRequired); return }
    setError('')
    setSaving(true)
    try {
      await onSave({
        title: title.trim(),
        category,
        status,
        priority,
        problem: problem.trim() || null,
        pic_main: picMain.trim() || null,
        pic_support: picSupport.trim() || null,
        due_date: dueDate || null,
      })
    } catch {
      setError(MSG.saveFailed)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex-1 p-5 overflow-y-auto">
      <h2 className="text-sm font-semibold text-white mb-1">
        {initial ? 'Edit Action Plan' : '+ New Action Plan'}
      </h2>
      <p className="text-[10px] text-gray-600 mb-4">
        Nhập thông tin proposal — AI sẽ generate timeline, checklist, input/output sau khi lưu.
      </p>

      <div className="mb-3">
        <label className="field-label">Title *</label>
        <input
          className="input-base"
          placeholder="Làm lại phân khúc RFM theo transaction interval..."
          value={title}
          onChange={e => setTitle(e.target.value)}
          autoFocus
        />
      </div>

      <div className="flex gap-2 mb-3">
        <div className="flex-1">
          <label className="field-label">Category</label>
          <select className="input-base" value={category} onChange={e => setCategory(e.target.value as APCategory)}>
            <option value="rfm">RFM</option>
            <option value="cohort">Cohort</option>
            <option value="statistical">Statistical</option>
            <option value="etl">ETL</option>
            <option value="dashboard">Dashboard</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div className="flex-1">
          <label className="field-label">Priority</label>
          <select className="input-base" value={priority} onChange={e => setPriority(e.target.value as APPriority)}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
        <div className="flex-1">
          <label className="field-label">Status</label>
          <select className="input-base" value={status} onChange={e => setStatus(e.target.value as APStatus)}>
            <option value="draft">Draft</option>
            <option value="proposed">Proposed</option>
            <option value="approved">Approved</option>
            <option value="in_progress">In Progress</option>
            <option value="done">Done</option>
          </select>
        </div>
      </div>

      <div className="mb-3">
        <label className="field-label">Problem / Mục tiêu</label>
        <textarea
          className="input-base resize-none"
          rows={4}
          placeholder="Mô tả vấn đề, bối cảnh, lý do muốn làm... Càng chi tiết AI càng generate tốt hơn."
          value={problem}
          onChange={e => setProblem(e.target.value)}
        />
      </div>

      <div className="flex gap-2 mb-3">
        <div className="flex-1">
          <label className="field-label">PIC Chính</label>
          <input className="input-base" placeholder="Leonie" value={picMain} onChange={e => setPicMain(e.target.value)} />
        </div>
        <div className="flex-1">
          <label className="field-label">PIC Phụ</label>
          <input className="input-base" placeholder="Nguyen Van A" value={picSupport} onChange={e => setPicSupport(e.target.value)} />
        </div>
        <div className="flex-1">
          <label className="field-label">Due Date</label>
          <input type="date" className="input-base" value={dueDate} onChange={e => setDueDate(e.target.value)} />
        </div>
      </div>

      {error && <p className="text-danger text-xs mb-3">{error}</p>}

      <button
        onClick={handleSubmit}
        disabled={saving}
        className="btn-primary w-full mb-2 flex items-center justify-center gap-1.5 disabled:opacity-50"
      >
        <Check size={13} /> {saving ? 'Saving...' : 'Save Plan'}
      </button>
      <button onClick={onCancel} className="btn-ghost w-full flex items-center justify-center gap-1.5">
        <X size={13} /> Cancel
      </button>
    </div>
  )
}
