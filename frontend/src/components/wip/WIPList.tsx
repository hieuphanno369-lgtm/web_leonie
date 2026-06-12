import { Plus } from 'lucide-react'
import type { WIPItem } from '../../types'
import WIPItemComponent from './WIPItem'
import { useResizableSidebar, ResizeHandle } from '../layout/ResizableSidebar'
import { MSG } from '../../messages'

interface Props {
  wips: WIPItem[]
  selectedId: string | null
  onSelect: (id: string) => void
  onNew: () => void
}

export default function WIPList({ wips, selectedId, onSelect, onNew }: Props) {
  const { width, onDragStart } = useResizableSidebar({
    initial: 340, min: 260, max: 620, storageKey: 'leonie:wip-sidebar-w',
  })
  return (
    <>
    <div style={{ width }} className="border-r border-white/5 flex flex-col flex-shrink-0 h-full">
      <div className="px-4 pt-3.5 pb-3 border-b border-white/5 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white">WIP Builder</h2>
        <button onClick={onNew} className="btn-primary flex items-center gap-1 text-xs px-2.5 py-1">
          <Plus size={12} /> New
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-2 pt-2 pb-3">
        {wips.length === 0 ? (
          <p className="text-center text-gray-600 text-xs mt-8">{MSG.emptyWipList}</p>
        ) : (
          wips.map(w => (
            <WIPItemComponent
              key={w.id}
              wip={w}
              isSelected={w.id === selectedId}
              onSelect={() => onSelect(w.id)}
            />
          ))
        )}
      </div>
    </div>
    <ResizeHandle onDragStart={onDragStart} color="work" />
    </>
  )
}
