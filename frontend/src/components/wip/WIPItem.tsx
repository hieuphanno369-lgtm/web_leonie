import type { WIPItem } from '../../types'

interface Props {
  wip: WIPItem
  isSelected: boolean
  onSelect: () => void
}

function progressColor(p: number) {
  if (p >= 100) return 'bg-work'
  if (p >= 70)  return 'bg-warning'
  return 'bg-data'
}

function progressTextColor(p: number) {
  if (p >= 100) return 'text-work'
  if (p >= 70)  return 'text-warning'
  return 'text-data'
}

export default function WIPItem({ wip, isSelected, onSelect }: Props) {
  return (
    <div
      onClick={onSelect}
      className={`rounded-lg px-3 py-2.5 mb-1 cursor-pointer border transition-all ${
        isSelected
          ? 'bg-data/5 border-data/20'
          : 'border-white/5 hover:bg-white/3 hover:border-white/10'
      }`}
    >
      <p className="text-xs font-medium text-white truncate mb-2">{wip.task_title}</p>
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${progressColor(wip.progress)}`}
            style={{ width: `${wip.progress}%` }}
          />
        </div>
        <span className={`text-[11px] font-semibold tabular-nums ${progressTextColor(wip.progress)}`}>
          {wip.progress}%
        </span>
      </div>
    </div>
  )
}
