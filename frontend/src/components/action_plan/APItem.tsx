import type { ActionPlan } from '../../types'

const statusCls: Record<string, string> = {
  draft:       'bg-white/5 text-gray-400 border-white/10',
  proposed:    'bg-data/10 text-data border-data/25',
  approved:    'bg-work/10 text-work border-work/25',
  in_progress: 'bg-warning/10 text-warning border-warning/25',
  done:        'bg-work/10 text-work border-work/25',
}

const catLabel: Record<string, string> = {
  rfm: 'RFM', cohort: 'Cohort', statistical: 'Stats',
  etl: 'ETL', dashboard: 'Dashboard', other: 'Other',
}

interface Props {
  plan: ActionPlan
  isSelected: boolean
  onSelect: (id: string) => void
}

export default function APItem({ plan, isSelected, onSelect }: Props) {
  const hasAI = !!(plan.ai_timeline || plan.ai_checklist)

  return (
    <button
      onClick={() => onSelect(plan.id)}
      className={`w-full text-left px-3 py-2.5 rounded-lg mb-1 transition-all border ${
        isSelected
          ? 'bg-white/5 border-white/10 text-white'
          : 'border-transparent text-gray-400 hover:text-white hover:bg-white/3'
      }`}
    >
      <div className="flex items-center gap-1.5 mb-1">
        <span className={`badge border text-[9px] ${statusCls[plan.status]}`}>
          {plan.status.replace('_', ' ')}
        </span>
        <span className="badge bg-white/5 text-gray-500 border-white/10 text-[9px]">
          {catLabel[plan.category]}
        </span>
        {hasAI && (
          <span className="ml-auto text-[9px] text-learn opacity-60">AI</span>
        )}
      </div>
      <p className="text-xs font-medium leading-snug line-clamp-2">{plan.title}</p>
      {plan.pic_main && (
        <p className="text-[10px] text-gray-600 mt-0.5">{plan.pic_main}</p>
      )}
    </button>
  )
}
