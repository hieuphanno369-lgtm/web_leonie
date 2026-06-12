import { useState } from 'react'
import { Plus, Trash2, Check, X } from 'lucide-react'
import type { StreakRule, StreakCondition } from '../../types'

interface Props {
  rule: StreakRule
  onSave: (rule: StreakRule) => void
  onCancel: () => void
}

const CONDITION_TYPES: { value: StreakCondition['type']; label: string }[] = [
  { value: 'tasks_done',  label: 'Tasks done' },
  { value: 'eda_done',    label: 'EDA done' },
  { value: 'kpi_logged',  label: 'KPI logged' },
  { value: 'wip_updated', label: 'WIP updated' },
]

export default function RuleEditor({ rule, onSave, onCancel }: Props) {
  const [conditions, setConditions] = useState<StreakCondition[]>(rule.conditions)
  const [logic, setLogic] = useState<'AND' | 'OR'>(rule.logic)

  function addCondition() {
    setConditions(cs => [...cs, { type: 'tasks_done', op: 'gte', value: 1 }])
  }

  function removeCondition(i: number) {
    setConditions(cs => cs.filter((_, j) => j !== i))
  }

  function updateCondition(i: number, patch: Partial<StreakCondition>) {
    setConditions(cs => cs.map((c, j) => j === i ? { ...c, ...patch } : c))
  }

  return (
    <div className="bg-secondary border border-white/8 rounded-xl p-4 w-full max-w-sm">
      <h3 className="text-sm font-semibold text-white mb-3">Edit Streak Rule</h3>

      <div className="space-y-2 mb-3">
        {conditions.map((c, i) => (
          <div key={i} className="flex items-center gap-2">
            <select
              className="input-base text-xs flex-1"
              value={c.type}
              onChange={e => updateCondition(i, { type: e.target.value as StreakCondition['type'] })}
            >
              {CONDITION_TYPES.map(ct => <option key={ct.value} value={ct.value}>{ct.label}</option>)}
            </select>
            <span className="text-gray-600 text-xs">≥</span>
            <input
              type="number" min={1} className="input-base text-xs w-14"
              value={c.value}
              onChange={e => updateCondition(i, { value: Number(e.target.value) })}
            />
            <button onClick={() => removeCondition(i)} className="text-gray-600 hover:text-danger">
              <Trash2 size={12} />
            </button>
          </div>
        ))}
      </div>

      {conditions.length > 1 && (
        <div className="flex gap-2 mb-3">
          <span className="text-gray-600 text-xs">Combine with:</span>
          {(['AND', 'OR'] as const).map(l => (
            <button
              key={l}
              onClick={() => setLogic(l)}
              className={`text-xs px-2 py-0.5 rounded border transition-all ${
                logic === l ? 'bg-analytics/10 text-analytics border-analytics/30' : 'text-gray-500 border-white/10'
              }`}
            >
              {l}
            </button>
          ))}
        </div>
      )}

      <button
        onClick={addCondition}
        className="btn-ghost w-full text-xs flex items-center justify-center gap-1 mb-3"
      >
        <Plus size={11} /> Add condition
      </button>

      <div className="flex gap-2">
        <button
          onClick={() => onSave({ conditions, logic })}
          disabled={conditions.length === 0}
          className="btn-primary flex-1 flex items-center justify-center gap-1 text-xs disabled:opacity-50"
        >
          <Check size={12} /> Save
        </button>
        <button onClick={onCancel} className="btn-ghost flex-1 flex items-center justify-center gap-1 text-xs">
          <X size={12} /> Cancel
        </button>
      </div>
    </div>
  )
}
