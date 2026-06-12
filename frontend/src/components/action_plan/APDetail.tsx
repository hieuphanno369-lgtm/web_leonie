import { useState, useEffect } from 'react'
import { Pencil, Trash2, Sparkles, RefreshCw, Send, CheckSquare, Square } from 'lucide-react'
import type { ActionPlan, ChecklistItem, TimelineItem, APInput, APOutput, APRef } from '../../types'
import { generatePlan, refinePlan, updatePlan } from '../../api/action_plan'

interface Props {
  plan: ActionPlan
  onEdit: () => void
  onDelete: (id: string) => void
  onUpdated: (plan: ActionPlan) => void
}

const statusCls: Record<string, string> = {
  draft:       'bg-white/5 text-gray-400 border-white/10',
  proposed:    'bg-data/10 text-data border-data/25',
  approved:    'bg-work/10 text-work border-work/25',
  in_progress: 'bg-warning/10 text-warning border-warning/25',
  done:        'bg-work/10 text-work border-work/25',
}
const approvalCls: Record<string, string> = {
  pending:  'bg-warning/10 text-warning border-warning/25',
  approved: 'bg-work/10 text-work border-work/25',
  rejected: 'bg-danger/10 text-danger border-danger/25',
}
const priorityCls: Record<string, string> = {
  high:   'bg-danger/10 text-danger border-danger/25',
  medium: 'bg-data/10 text-data border-data/25',
  low:    'bg-white/5 text-gray-500 border-white/10',
}

function parseJson<T>(raw: string | null | undefined, fallback: T): T {
  if (!raw) return fallback
  try { return JSON.parse(raw) as T } catch { return fallback }
}

const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })

export default function APDetail({ plan, onEdit, onDelete, onUpdated }: Props) {
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [generating,    setGenerating]    = useState(false)
  const [condition,     setCondition]     = useState('')
  const [refining,      setRefining]      = useState(false)
  const [aiError,       setAiError]       = useState('')
  const [checklist,     setChecklist]     = useState<ChecklistItem[]>([])

  const timeline = parseJson<TimelineItem[]>(plan.ai_timeline, [])
  const aiInput  = parseJson<APInput>(plan.ai_input, { sources: [], tables: [], notes: '' })
  const aiOutput = parseJson<APOutput>(plan.ai_output, { deliverable: '', format: '' })
  const refs     = parseJson<APRef[]>(plan.ai_refs, [])
  const hasAI    = timeline.length > 0 || checklist.length > 0

  useEffect(() => {
    setConfirmDelete(false)
    setChecklist(parseJson<ChecklistItem[]>(plan.ai_checklist, []))
  }, [plan.id, plan.ai_checklist])

  async function handleGenerate() {
    setGenerating(true); setAiError('')
    try {
      const updated = await generatePlan(plan.id)
      onUpdated(updated)
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string }; status?: number }; message?: string }
      const detail = axiosErr?.response?.data?.detail
        ?? (axiosErr?.response?.status ? `HTTP ${axiosErr.response.status}` : null)
        ?? axiosErr?.message
        ?? 'Lỗi không xác định'
      setAiError(`AI tạo kế hoạch thất bại: ${detail}`)
    } finally {
      setGenerating(false)
    }
  }

  async function handleRefine() {
    if (!condition.trim()) return
    setRefining(true); setAiError('')
    try {
      const updated = await refinePlan(plan.id, condition.trim())
      onUpdated(updated)
      setCondition('')
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setAiError(detail ?? 'AI tinh chỉnh thất bại — lỗi không xác định')
    } finally {
      setRefining(false)
    }
  }

  async function toggleCheck(idx: number) {
    const next = checklist.map((c, i) => i === idx ? { ...c, done: !c.done } : c)
    setChecklist(next)
    try {
      const updated = await updatePlan(plan.id, { ai_checklist: JSON.stringify(next) })
      onUpdated(updated)
    } catch { /* revert on next prop */ }
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="p-5">
        <div className="flex items-start justify-between gap-3 mb-3">
          <h2 className="text-base font-semibold text-white leading-snug">{plan.title}</h2>
          <div className="flex gap-2 flex-shrink-0">
            <button onClick={onEdit} className="btn-ghost flex items-center gap-1 text-xs px-2.5 py-1">
              <Pencil size={12} /> Edit
            </button>
            {confirmDelete ? (
              <button onClick={() => onDelete(plan.id)} className="btn-danger flex items-center gap-1 text-xs px-2.5 py-1">
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

        <div className="flex flex-wrap gap-1.5 mb-4">
          <span className={`badge border ${statusCls[plan.status]}`}>{plan.status.replace('_', ' ')}</span>
          <span className={`badge border ${priorityCls[plan.priority]}`}>{plan.priority}</span>
          <span className={`badge border ${approvalCls[plan.approval]}`}>{plan.approval}</span>
          {plan.due_date && (
            <span className="badge bg-white/5 text-gray-400 border border-white/10">{fmtDate(plan.due_date)}</span>
          )}
        </div>

        <hr className="border-white/5 mb-4" />

        {plan.problem && (
          <div className="mb-4">
            <p className="field-label mb-2">Problem / Mục tiêu</p>
            <div className="bg-secondary border border-white/5 rounded-lg px-3 py-2.5 text-xs text-gray-300 leading-relaxed whitespace-pre-wrap">
              {plan.problem}
            </div>
          </div>
        )}

        <div className="flex gap-4 mb-4 text-xs">
          {plan.pic_main && (
            <div><p className="field-label mb-1">PIC Chính</p><p className="text-gray-300">{plan.pic_main}</p></div>
          )}
          {plan.pic_support && (
            <div><p className="field-label mb-1">PIC Phụ</p><p className="text-gray-300">{plan.pic_support}</p></div>
          )}
          <div><p className="field-label mb-1">Category</p><p className="text-gray-300 uppercase text-[10px]">{plan.category}</p></div>
        </div>

        <hr className="border-white/5 mb-4" />

        <div className="mb-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-[10px] uppercase tracking-widest text-learn/70 font-semibold flex items-center gap-1.5">
              <Sparkles size={11} /> AI Generated Plan
            </p>
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="btn-ghost text-[10px] px-2.5 py-1 flex items-center gap-1 text-learn border-learn/30 hover:border-learn/60 disabled:opacity-40"
            >
              <RefreshCw size={10} className={generating ? 'animate-spin' : ''} />
              {hasAI ? 'Regenerate' : 'Generate Plan'}
            </button>
          </div>

          {aiError && <p className="text-danger text-xs mb-3">{aiError}</p>}
          {generating && (
            <div className="text-xs text-gray-500 italic mb-3 flex items-center gap-2">
              <RefreshCw size={11} className="animate-spin" /> AI đang tạo plan...
            </div>
          )}

          {hasAI && (
            <div className="space-y-4">
              {timeline.length > 0 && (
                <div>
                  <p className="field-label mb-2">Timeline</p>
                  <div className="space-y-1.5">
                    {timeline.map((t, i) => (
                      <div key={i} className="flex gap-2 text-xs">
                        <span className="text-work font-mono text-[10px] w-14 flex-shrink-0 pt-0.5">{t.week}</span>
                        <span className="text-gray-300 leading-relaxed">{t.tasks}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {checklist.length > 0 && (
                <div>
                  <p className="field-label mb-2">
                    Checklist ({checklist.filter(c => c.done).length}/{checklist.length})
                  </p>
                  <div className="space-y-1">
                    {checklist.map((c, i) => (
                      <button
                        key={i}
                        onClick={() => toggleCheck(i)}
                        className="flex items-start gap-2 text-xs text-left w-full group hover:text-white transition-colors"
                      >
                        {c.done
                          ? <CheckSquare size={13} className="text-work flex-shrink-0 mt-0.5" />
                          : <Square size={13} className="text-gray-600 flex-shrink-0 mt-0.5 group-hover:text-gray-400" />
                        }
                        <span className={c.done ? 'text-gray-500 line-through' : 'text-gray-300'}>{c.text}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                {aiInput.sources.length > 0 && (
                  <div>
                    <p className="field-label mb-1.5">Input Sources</p>
                    <div className="bg-secondary border border-white/5 rounded-lg p-2.5 text-xs">
                      <p className="text-gray-400 mb-1">{aiInput.sources.join(', ')}</p>
                      {aiInput.tables.length > 0 && (
                        <p className="text-gray-600 font-mono text-[10px]">{aiInput.tables.join(', ')}</p>
                      )}
                      {aiInput.notes && <p className="text-gray-500 mt-1">{aiInput.notes}</p>}
                    </div>
                  </div>
                )}
                {aiOutput.deliverable && (
                  <div>
                    <p className="field-label mb-1.5">Output</p>
                    <div className="bg-secondary border border-white/5 rounded-lg p-2.5 text-xs">
                      <p className="text-gray-400 mb-1">{aiOutput.deliverable}</p>
                      {aiOutput.format && <p className="text-gray-600 text-[10px]">{aiOutput.format}</p>}
                    </div>
                  </div>
                )}
              </div>

              {(plan.ai_value || plan.ai_impact) && (
                <div className="bg-work/5 border border-work/15 rounded-lg p-3 space-y-2">
                  {plan.ai_value && (
                    <div>
                      <p className="field-label mb-1">Value</p>
                      <p className="text-xs text-gray-300">{plan.ai_value}</p>
                    </div>
                  )}
                  {plan.ai_impact && (
                    <div>
                      <p className="field-label mb-1">Impact</p>
                      <p className="text-xs text-gray-300">{plan.ai_impact}</p>
                    </div>
                  )}
                </div>
              )}

              {refs.length > 0 && (
                <div>
                  <p className="field-label mb-2">References</p>
                  <div className="space-y-2">
                    {refs.map((r, i) => (
                      <div key={i} className="bg-secondary border border-white/5 rounded-lg px-3 py-2 text-xs">
                        <p className="text-white font-medium">{r.company}</p>
                        <p className="text-data text-[10px] mb-0.5">{r.method}</p>
                        <p className="text-gray-400 leading-relaxed">{r.summary}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {plan.ai_suggestions && (
                <div>
                  <p className="field-label mb-1">Đề xuất thêm</p>
                  <p className="text-xs text-gray-400 leading-relaxed">{plan.ai_suggestions}</p>
                </div>
              )}
            </div>
          )}

          {hasAI && (
            <div className="mt-4 border-t border-white/5 pt-4">
              <p className="field-label mb-2">Add Condition / Điều kiện mới</p>
              <div className="flex gap-2">
                <textarea
                  className="input-base flex-1 resize-none text-xs"
                  rows={2}
                  placeholder="VD: Chia thêm theo account source organic vs PG..."
                  value={condition}
                  onChange={e => setCondition(e.target.value)}
                />
                <button
                  onClick={handleRefine}
                  disabled={refining || !condition.trim()}
                  className="btn-primary px-3 flex items-center gap-1.5 self-end text-xs disabled:opacity-40"
                >
                  <Send size={11} className={refining ? 'animate-pulse' : ''} />
                  {refining ? '...' : 'Update'}
                </button>
              </div>
            </div>
          )}
        </div>

        <hr className="border-white/5 mb-4" />

        <div className="mb-4">
          <p className="field-label mb-2">Manager Review</p>
          <div className="bg-secondary border border-white/5 rounded-lg px-3 py-2.5 text-xs text-gray-400 min-h-[48px] whitespace-pre-wrap">
            {plan.manager_notes ?? <span className="italic text-gray-600">Chưa có góp ý</span>}
          </div>
        </div>

        <p className="text-[10px] text-gray-600">
          Created: <span className="text-gray-500">{fmtDate(plan.created)}</span>
          {' · '}
          Updated: <span className="text-gray-500">{fmtDate(plan.updated)}</span>
        </p>
      </div>
    </div>
  )
}
