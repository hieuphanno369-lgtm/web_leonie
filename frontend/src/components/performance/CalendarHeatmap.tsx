import type { DayStatus } from '../../types'

interface Props {
  calendar: DayStatus[]
}

const statusColor: Record<string, string> = {
  hit:     'bg-work opacity-90',
  partial: 'bg-warning opacity-80',
  miss:    'bg-white/5',
}

export default function CalendarHeatmap({ calendar }: Props) {
  return (
    <div className="bg-secondary border border-white/5 rounded-lg p-4">
      <p className="text-[10px] uppercase tracking-widest text-gray-600 mb-3">Last 30 days</p>
      <div className="flex flex-wrap gap-1.5">
        {calendar.map(({ date, status }) => (
          <div
            key={date}
            title={`${date}: ${status}`}
            className={`w-5 h-5 rounded-sm cursor-default ${statusColor[status]}`}
          />
        ))}
      </div>
      <div className="flex gap-4 mt-3">
        {[
          { color: 'bg-work',    label: 'Hit' },
          { color: 'bg-warning', label: 'Partial' },
          { color: 'bg-white/5', label: 'Miss' },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-1.5">
            <div className={`w-3 h-3 rounded-sm ${color}`} />
            <span className="text-[10px] text-gray-600">{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
