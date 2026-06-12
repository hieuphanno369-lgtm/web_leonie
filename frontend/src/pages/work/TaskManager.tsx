import { useEffect, useState, useCallback } from 'react'
import type { Task } from '../../types'
import { fetchTasks, createTask, updateTask, deleteTask } from '../../api/tasks'
import type { TaskPayload } from '../../api/tasks'
import TaskList   from '../../components/tasks/TaskList'
import TaskDetail from '../../components/tasks/TaskDetail'
import TaskForm   from '../../components/tasks/TaskForm'
import { MSG } from '../../messages'

type PanelMode = 'empty' | 'detail' | 'create' | 'edit'

export default function TaskManager() {
  const [tasks,      setTasks]      = useState<Task[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [mode,       setMode]       = useState<PanelMode>('empty')
  const [apiError,   setApiError]   = useState('')

  const selectedTask = tasks.find(t => t.id === selectedId) ?? null

  const load = useCallback(async () => {
    try {
      const data = await fetchTasks()
      setTasks(data)
      setApiError('')
    } catch {
      setApiError(MSG.apiUnreachable)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // ── Handlers ───────────────────────────────────────────────────────────────

  function handleSelect(id: string) {
    setSelectedId(id)
    setMode('detail')
  }

  async function handleToggleDone(id: string) {
    const task = tasks.find(t => t.id === id)
    if (!task) return
    const newStatus = task.status === 'done' ? 'todo' : 'done'
    try {
      const updated = await updateTask(id, { status: newStatus })
      setTasks(ts => ts.map(t => t.id === id ? updated : t))
    } catch {
      setApiError(MSG.updateFailed)
    }
  }

  async function handleSave(payload: TaskPayload) {
    try {
      if (mode === 'create') {
        const created = await createTask(payload)
        setTasks(ts => [created, ...ts])
        setSelectedId(created.id)
        setMode('detail')
      } else if (mode === 'edit' && selectedId) {
        const updated = await updateTask(selectedId, payload)
        setTasks(ts => ts.map(t => t.id === selectedId ? updated : t))
        setMode('detail')
      }
    } catch {
      setApiError(MSG.saveFailed)
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteTask(id)
      setTasks(ts => ts.filter(t => t.id !== id))
      setSelectedId(null)
      setMode('empty')
    } catch {
      setApiError(MSG.deleteFailed)
    }
  }

  function handleCancel() {
    setMode(selectedTask ? 'detail' : 'empty')
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen overflow-hidden">
      <TaskList
        tasks={tasks}
        selectedId={selectedId}
        onSelect={handleSelect}
        onToggleDone={handleToggleDone}
        onNewTask={() => { setSelectedId(null); setMode('create') }}
      />

      <div className="flex-1 flex overflow-hidden relative">
        {apiError && (
          <div className="absolute top-4 right-4 bg-danger/10 border border-danger/30 text-danger text-xs px-3 py-2 rounded-lg">
            {apiError}
          </div>
        )}

        {mode === 'empty' && (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-600 text-sm gap-2">
            <span className="text-3xl opacity-20">☐</span>
            <p>{MSG.emptySelectTask}</p>
          </div>
        )}

        {mode === 'detail' && selectedTask && (
          <TaskDetail
            task={selectedTask}
            onEdit={() => setMode('edit')}
            onDelete={handleDelete}
          />
        )}

        {(mode === 'create' || mode === 'edit') && (
          <TaskForm
            initial={mode === 'edit' ? (selectedTask ?? undefined) : undefined}
            onSave={handleSave}
            onCancel={handleCancel}
          />
        )}
      </div>
    </div>
  )
}
