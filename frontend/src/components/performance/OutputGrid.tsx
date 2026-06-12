import type { PerformanceSummary } from '../../types'

interface Props {
  summary: PerformanceSummary
}

export default function OutputGrid({ summary }: Props) {
  const items = [
    { label: 'Tasks done',    value: summary.tasks_done,              color: 'text-work',      note: 'this month' },
    { label: 'EDA completed', value: summary.eda_done,                color: 'text-data',      note: 'this month' },
    { label: 'KPI logs',      value: summary.kpi_logs,                color: 'text-learn',     note: 'entries logged' },
    { label: 'WIP avg',       value: `${summary.wip_avg_progress}%`,  color: 'text-analytics', note: 'progress' },
  ]

  return (
    <div className="grid grid-cols-2 gap-3">
      {items.map(({ label, value, color, note }) => (
        <div key={label} className="bg-secondary border border-white/5 rounded-lg p-4">
          <p className="text-gray-600 text-[10px] uppercase tracking-widest mb-1">{label}</p>
          <p className={`text-2xl font-bold ${color}`}>{value}</p>
          <p className="text-gray-600 text-[10px] mt-0.5">{note}</p>
        </div>
      ))}
    </div>
  )
}
