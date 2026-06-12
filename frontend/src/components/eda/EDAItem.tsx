import type { EDARequest } from '../../types'

interface Props {
  eda: EDARequest
  isSelected: boolean
  onSelect: () => void
}

const priorityBadge: Record<string, string> = {
  high:   'bg-danger/10 text-danger border-danger/25',
  medium: 'bg-data/10 text-data border-data/25',
  low:    'bg-white/5 text-gray-500 border-white/10',
}

const statusDot: Record<string, string> = {
  todo:        'bg-warning',
  in_progress: 'bg-data',
  done:        'bg-work',
}

export default function EDAItem({ eda, isSelected, onSelect }: Props) {
  const done = eda.status === 'done'
  return (
    <div
      onClick={onSelect}
      className={`rounded-lg px-3 py-2.5 mb-1 cursor-pointer border transition-all ${
        isSelected
          ? 'bg-work/5 border-work/20'
          : 'border-white/5 hover:bg-white/3 hover:border-white/10'
      } ${done ? 'opacity-50' : ''}`}
    >
      <div className="flex items-center gap-2 mb-1">
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${statusDot[eda.status]}`} />
        <span className={`text-xs font-medium flex-1 truncate ${done ? 'line-through text-gray-500' : 'text-white'}`}>
          {eda.title}
        </span>
        <span className={`badge border text-[10px] ${priorityBadge[eda.priority]}`}>
          {eda.priority.toUpperCase()}
        </span>
      </div>
      <p className="text-[11px] text-gray-500 truncate pl-4">{eda.requester} · {eda.dataset}</p>
    </div>
  )
}
