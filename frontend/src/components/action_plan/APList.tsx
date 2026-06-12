import { useState } from 'react'
import { Plus } from 'lucide-react'
import type { ActionPlan, APStatus } from '../../types'
import APItem from './APItem'
import { useResizableSidebar, ResizeHandle } from '../layout/ResizableSidebar'

const TABS: { label: string; value: APStatus | 'all' }[] = [
  { label: 'All',         value: 'all' },
  { label: 'Draft',       value: 'draft' },
  { label: 'Proposed',    value: 'proposed' },
  { label: 'Approved',    value: 'approved' },
  { label: 'Done',        value: 'done' },
]

interface Props {
  plans: ActionPlan[]
  selectedId: string | null
  onSelect: (id: string) => void
  onNew: () => void
}

export default function APList({ plans, selectedId, onSelect, onNew }: Props) {
  const [tab,    setTab]    = useState<APStatus | 'all'>('all')
  const [search, setSearch] = useState('')
  const { width, onDragStart } = useResizableSidebar({
    initial: 256, min: 200, max: 520, storageKey: 'leonie:ap-sidebar-w',
  })

  const visible = plans.filter(p => {
    const matchTab = tab === 'all' || p.status === tab
    const matchQ   = !search || p.title.toLowerCase().includes(search.toLowerCase())
    return matchTab && matchQ
  })

  return (
    <>
    <div style={{ width }} className="flex-shrink-0 border-r border-white/5 flex flex-col overflow-hidden">
      <div className="p-3 border-b border-white/5">
        <div className="flex items-center justify-between mb-2.5">
          <h2 className="text-xs font-semibold text-white">Action Plans</h2>
          <button onClick={onNew} className="btn-primary px-2 py-1 text-[10px] flex items-center gap-1">
            <Plus size={11} /> New
          </button>
        </div>

        <div className="flex gap-1 flex-wrap mb-2">
          {TABS.map(t => (
            <button
              key={t.value}
              onClick={() => setTab(t.value)}
              className={`text-[10px] px-2 py-0.5 rounded-full transition-all ${
                tab === t.value
                  ? 'bg-work/20 text-work border border-work/30'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {t.label}
              {t.value !== 'all' && (
                <span className="ml-0.5 opacity-50">
                  ({plans.filter(p => p.status === t.value).length})
                </span>
              )}
            </button>
          ))}
        </div>

        <input
          className="input-base text-xs py-1.5"
          placeholder="Tìm kế hoạch..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {visible.length === 0 ? (
          <p className="text-[11px] text-gray-600 text-center mt-6 px-2">No plans found</p>
        ) : (
          visible.map(p => (
            <APItem key={p.id} plan={p} isSelected={p.id === selectedId} onSelect={onSelect} />
          ))
        )}
      </div>
    </div>
    <ResizeHandle onDragStart={onDragStart} color="work" />
    </>
  )
}
