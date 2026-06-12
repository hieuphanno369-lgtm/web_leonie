import { Flame, Settings } from 'lucide-react'
import type { StreakRule } from '../../types'

interface Props {
  streak: number
  rule: StreakRule
  onEditRule: () => void
}

function ruleText(rule: StreakRule): string {
  const parts = rule.conditions.map(c => {
    const labels: Record<string, string> = {
      tasks_done: 'tasks done', eda_done: 'EDA done',
      kpi_logged: 'KPI logged', wip_updated: 'WIP updated',
    }
    return `≥${c.value} ${labels[c.type] ?? c.type}`
  })
  return parts.join(` ${rule.logic} `)
}

export default function StreakCard({ streak, rule, onEditRule }: Props) {
  return (
    <div className="w-[200px] flex-shrink-0 bg-secondary border border-white/5 rounded-xl p-5 flex flex-col items-center justify-center gap-3">
      <Flame size={36} className="text-warning" />
      <div className="text-center">
        <p className="text-warning text-4xl font-extrabold leading-none">{streak}</p>
        <p className="text-gray-500 text-xs mt-1">day streak</p>
      </div>
      <div className="text-center">
        <p className="text-[10px] text-gray-600 leading-relaxed">{ruleText(rule)}</p>
      </div>
      <button
        onClick={onEditRule}
        className="btn-ghost flex items-center gap-1 text-xs px-2.5 py-1"
      >
        <Settings size={11} /> Edit Rule
      </button>
    </div>
  )
}
