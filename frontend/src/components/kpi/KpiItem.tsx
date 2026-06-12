import { Trash2 } from 'lucide-react'
import type { KpiEntry } from '../../types'

interface Props {
  entry: KpiEntry
  isSelected: boolean
  onSelect: () => void
  onDelete: () => void
}

const catColor: Record<string, string> = {
  da_output: 'bg-work/10 text-work border-work/25',
  business:  'bg-data/10 text-data border-data/25',
}
const catLabel: Record<string, string> = { da_output: 'DA', business: 'BIZ' }

export default function KpiItem({ entry, isSelected, onSelect, onDelete }: Props) {
  return (
    <div
      onClick={onSelect}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer border mb-0.5 transition-all group
        ${isSelected ? 'bg-analytics/5 border-analytics/30' : 'border-transparent hover:bg-white/5 hover:border-white/5'}`}
    >
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-200 truncate">{entry.metric}</p>
        <div className="flex items-center gap-1.5 mt-0.5">
          <span className={`badge border text-[9px] ${catColor[entry.category]}`}>
            {catLabel[entry.category]}
          </span>
          <span className="text-[10px] text-gray-600">{entry.date}</span>
        </div>
      </div>
      <span className="text-sm font-semibold text-analytics tabular-nums flex-shrink-0">
        {entry.value.toLocaleString('vi-VN')}
      </span>
      <button
        onClick={e => { e.stopPropagation(); onDelete() }}
        className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-danger transition-opacity flex-shrink-0"
      >
        <Trash2 size={12} />
      </button>
    </div>
  )
}
