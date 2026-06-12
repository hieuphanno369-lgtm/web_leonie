import { useState } from 'react'
import { Plus } from 'lucide-react'
import type { EDARequest, EDAStatus } from '../../types'
import EDAItem from './EDAItem'

type FilterTab = 'all' | EDAStatus

interface Props {
  requests: EDARequest[]
  selectedId: string | null
  onSelect: (id: string) => void
  onNew: () => void
}

export default function EDAList({ requests, selectedId, onSelect, onNew }: Props) {
  const [filter, setFilter] = useState<FilterTab>('all')
  const [search, setSearch] = useState('')

  const visible = requests.filter(r => {
    if (filter !== 'all' && r.status !== filter) return false
    if (search && !r.title.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const count = (f: FilterTab) =>
    f === 'all' ? requests.length : requests.filter(r => r.status === f).length

  const tabs: { key: FilterTab; label: string }[] = [
    { key: 'all',         label: 'All' },
    { key: 'todo',        label: 'Todo' },
    { key: 'in_progress', label: 'In Progress' },
    { key: 'done',        label: 'Done' },
  ]

  return (
    <div className="w-[340px] border-r border-white/5 flex flex-col flex-shrink-0 h-full">
      <div className="px-4 pt-3.5 pb-2.5 border-b border-white/5">
        <div className="flex items-center justify-between mb-2.5">
          <h2 className="text-sm font-semibold text-white">EDA Requests</h2>
          <button onClick={onNew} className="btn-primary flex items-center gap-1 text-xs px-2.5 py-1">
            <Plus size={12} /> New
          </button>
        </div>
        <div className="flex gap-1 flex-wrap">
          {tabs.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`px-2 py-1 rounded text-[11px] transition-all ${
                filter === key
                  ? 'bg-work/10 text-work border border-work/30'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {label} <span className="opacity-50">({count(key)})</span>
            </button>
          ))}
        </div>
      </div>
      <div className="mx-3 my-2">
        <input
          className="input-base text-xs"
          placeholder="Tìm yêu cầu EDA..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>
      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {visible.length === 0 ? (
          <p className="text-center text-gray-600 text-xs mt-8">No requests found</p>
        ) : (
          visible.map(r => (
            <EDAItem
              key={r.id}
              eda={r}
              isSelected={r.id === selectedId}
              onSelect={() => onSelect(r.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}
