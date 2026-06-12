import { CheckSquare, Square, Circle } from 'lucide-react'
import type { Task } from '../../types'

interface Props {
  task: Task
  isSelected: boolean
  onSelect: () => void
  onToggleDone: () => void
}

export default function TaskItem({ task, isSelected, onSelect, onToggleDone }: Props) {
  const isDone = task.status === 'done'

  return (
    <div
      onClick={onSelect}
      className={`flex items-start gap-2 px-3 py-2 rounded-lg cursor-pointer border mb-0.5 transition-all
        ${isSelected ? 'bg-work/5 border-work/30' : 'border-transparent hover:bg-white/5 hover:border-white/5'}
        ${isDone ? 'opacity-45' : ''}`}
    >
      <button
        onClick={e => { e.stopPropagation(); onToggleDone() }}
        className="mt-0.5 flex-shrink-0 text-gray-500 hover:text-work transition-colors"
      >
        {isDone
          ? <CheckSquare size={14} className="text-work" />
          : task.status === 'in_progress'
            ? <Circle size={14} className="text-data fill-data/20" />
            : <Square size={14} />}
      </button>

      <div className="flex-1 min-w-0">
        <p className={`text-xs truncate ${isDone ? 'line-through text-gray-500' : 'text-gray-200'}`}>
          {task.title}
        </p>
        <div className="flex items-center gap-1.5 mt-1 flex-wrap">
          {task.type === 'eda' && (
            <span className="badge bg-analytics/15 text-analytics">🔬 EDA</span>
          )}
          <PriorityBadge priority={task.priority} />
          {task.dataset && (
            <span className="badge bg-white/5 text-gray-500 truncate max-w-[80px]">{task.dataset}</span>
          )}
          {task.recurring && (
            <span className="badge bg-learn/15 text-learn">{task.recurring}</span>
          )}
          {task.due_date && !isDone && <DueDate date={task.due_date} />}
        </div>
      </div>
    </div>
  )
}

function PriorityBadge({ priority }: { priority: Task['priority'] }) {
  const cls = {
    high:   'bg-warning/15 text-warning',
    medium: 'bg-data/15 text-data',
    low:    'bg-white/5 text-gray-500',
  }[priority]
  return <span className={`badge ${cls}`}>{priority}</span>
}

function DueDate({ date }: { date: string }) {
  const due = new Date(date + 'T00:00:00')
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const overdue = due < today
  const label = due.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' })
  return (
    <span className={`text-[10px] ${overdue ? 'text-danger' : 'text-gray-600'}`}>
      {overdue ? '⚠ ' : ''}{label}
    </span>
  )
}
