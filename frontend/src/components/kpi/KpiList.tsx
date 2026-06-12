import { useState } from 'react'
import { Plus } from 'lucide-react'
import type { KpiEntry, KpiCategory } from '../../types'
import KpiItem from './KpiItem'

type FilterTab = 'all' | KpiCategory

interface Props {
  entries: KpiEntry[]
  selectedId: string | null
  onSelect: (id: string) => void
  onDelete: (id: string) => void
  onNew: () => void
}

export default function KpiList({ entries, selectedId, onSelect, onDelete, onNew }: Props) {
  const [filter, setFilter] = useState<FilterTab>('all')

  const visible = filter === 'all' ? entries : entries.filter(e => e.category === filter)

  const tabs: { key: FilterTab; label: string }[] = [
    { key: 'all',       label: 'All' },
    { key: 'da_output', label: 'DA Output' },
    { key: 'business',  label: 'Business' },
  ]

  return (
    <div className="w-[300px] border-r border-white/5 flex flex-col flex-shrink-0 h-full">
      <div className="px-4 pt-3.5 pb-2.5 border-b border-white/5">
        <div className="flex items-center justify-between mb-2.5">
          <h2 className="text-sm font-semibold text-white">KPI Entries</h2>
          <button onClick={onNew} className="btn-primary flex items-center gap-1 text-xs px-2.5 py-1">
            <Plus size={12} /> Log
          </button>
        </div>
        <div className="flex gap-1">
          {tabs.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`px-2 py-1 rounded text-[11px] transition-all ${
                filter === key
                  ? 'bg-analytics/10 text-analytics border border-analytics/30'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-2 pt-2 pb-3">
        {visible.length === 0 ? (
          <p className="text-center text-gray-600 text-xs mt-8">No entries</p>
        ) : (
          visible.map(e => (
            <KpiItem
              key={e.id}
              entry={e}
              isSelected={e.id === selectedId}
              onSelect={() => onSelect(e.id)}
              onDelete={() => onDelete(e.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}
