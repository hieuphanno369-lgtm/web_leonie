import { useState } from 'react'
import { Plus } from 'lucide-react'
import type { Task, TaskStatus, TaskType } from '../../types'
import TaskItem from './TaskItem'
import { useResizableSidebar, ResizeHandle } from '../layout/ResizableSidebar'

type StatusFilter = 'all' | TaskStatus
type TypeFilter   = 'all' | TaskType

interface Props {
  tasks: Task[]
  selectedId: string | null
  onSelect: (id: string) => void
  onToggleDone: (id: string) => void
  onNewTask: () => void
}

export default function TaskList({ tasks, selectedId, onSelect, onToggleDone, onNewTask }: Props) {
  const [typeFilter,   setTypeFilter]   = useState<TypeFilter>('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [search,       setSearch]       = useState('')
  const { width, onDragStart } = useResizableSidebar({
    initial: 340, min: 260, max: 620, storageKey: 'leonie:task-sidebar-w',
  })

  const visible = tasks.filter(t => {
    if (typeFilter   !== 'all' && t.type   !== typeFilter)   return false
    if (statusFilter !== 'all' && t.status !== statusFilter) return false
    if (search && !t.title.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const countByType = (f: TypeFilter) =>
    f === 'all' ? tasks.length : tasks.filter(t => t.type === f).length

  const countByStatus = (f: StatusFilter) =>
    f === 'all' ? tasks.length : tasks.filter(t => t.status === f).length

  const typeTabsCfg: { key: TypeFilter; label: string }[] = [
    { key: 'all',  label: 'All' },
    { key: 'task', label: '☐ Task' },
    { key: 'eda',  label: '🔬 EDA' },
  ]

  const statusTabsCfg: { key: StatusFilter; label: string }[] = [
    { key: 'all',         label: 'All' },
    { key: 'todo',        label: 'Todo' },
    { key: 'in_progress', label: 'WIP' },
    { key: 'done',        label: 'Done' },
  ]

  return (
    <>
    <div style={{ width }} className="border-r border-white/5 flex flex-col flex-shrink-0 h-full">
      {/* Header */}
      <div className="px-4 pt-3.5 pb-2.5 border-b border-white/5">
        <div className="flex items-center justify-between mb-2.5">
          <h2 className="text-sm font-semibold text-white">Tasks</h2>
          <button onClick={onNewTask} className="btn-primary flex items-center gap-1 text-xs px-2.5 py-1">
            <Plus size={12} /> New
          </button>
        </div>
        {/* Type filter row */}
        <div className="flex gap-1 mb-1.5">
          {typeTabsCfg.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setTypeFilter(key)}
              className={`px-2 py-1 rounded text-[11px] transition-all ${
                typeFilter === key
                  ? 'bg-analytics/10 text-analytics border border-analytics/30'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {label} <span className="opacity-50">({countByType(key)})</span>
            </button>
          ))}
        </div>
        {/* Status filter row */}
        <div className="flex gap-1 flex-wrap">
          {statusTabsCfg.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setStatusFilter(key)}
              className={`px-2 py-1 rounded text-[11px] transition-all ${
                statusFilter === key
                  ? 'bg-work/10 text-work border border-work/30'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {label} <span className="opacity-50">({countByStatus(key)})</span>
            </button>
          ))}
        </div>
      </div>

      {/* Search */}
      <div className="mx-3 my-2">
        <input
          className="input-base text-xs"
          placeholder="Tìm task..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {visible.length === 0 ? (
          <p className="text-center text-gray-600 text-xs mt-8">No tasks found</p>
        ) : (
          visible.map(task => (
            <TaskItem
              key={task.id}
              task={task}
              isSelected={task.id === selectedId}
              onSelect={() => onSelect(task.id)}
              onToggleDone={() => onToggleDone(task.id)}
            />
          ))
        )}
      </div>
    </div>
    <ResizeHandle onDragStart={onDragStart} color="work" />
    </>
  )
}
