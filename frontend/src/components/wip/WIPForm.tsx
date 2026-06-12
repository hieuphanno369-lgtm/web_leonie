import { useState, useEffect } from 'react'
import { Check, X } from 'lucide-react'
import type { Task } from '../../types'
import { fetchTasks } from '../../api/tasks'
import { createWIP } from '../../api/wip'
import type { WIPItem } from '../../types'
import { MSG } from '../../messages'

interface Props {
  onCreated: (wip: WIPItem) => void
  onCancel: () => void
}

export default function WIPForm({ onCreated, onCancel }: Props) {
  const [tasks,    setTasks]    = useState<Task[]>([])
  const [taskId,   setTaskId]   = useState('')
  const [progress, setProgress] = useState(0)
  const [error,    setError]    = useState('')
  const [saving,   setSaving]   = useState(false)

  useEffect(() => {
    fetchTasks().then(setTasks).catch(() => setError(MSG.loadTasksFailed))
  }, [])

  async function handleSubmit() {
    if (!taskId) { setError(MSG.selectTaskRequired); return }
    setError('')
    setSaving(true)
    try {
      const wip = await createWIP(taskId, progress)
      onCreated(wip)
    } catch {
      setError(MSG.createWipFailed)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex-1 p-5 overflow-y-auto">
      <h2 className="text-sm font-semibold text-white mb-4">＋ New WIP</h2>

      <div className="mb-4">
        <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Task *</label>
        <select className="input-base" value={taskId} onChange={e => setTaskId(e.target.value)}>
          <option value="">— select a task —</option>
          {tasks.filter(t => t.status !== 'done').map(t => (
            <option key={t.id} value={t.id}>{t.title}</option>
          ))}
        </select>
      </div>

      <div className="mb-6">
        <div className="flex items-center justify-between mb-1.5">
          <label className="text-[10px] uppercase tracking-widest text-gray-600">Initial Progress</label>
          <span className="text-xs font-semibold text-data">{progress}%</span>
        </div>
        <input
          type="range" min={0} max={100}
          value={progress}
          className="w-full h-1.5 rounded-full appearance-none cursor-pointer bg-white/5 accent-data"
          onChange={e => setProgress(Number(e.target.value))}
        />
      </div>

      {error && <p className="text-danger text-xs mb-3">{error}</p>}

      <button onClick={handleSubmit} disabled={saving} className="btn-primary w-full mb-2 flex items-center justify-center gap-1.5 disabled:opacity-50">
        <Check size={13} /> {saving ? 'Creating...' : 'Create WIP'}
      </button>
      <button onClick={onCancel} className="btn-ghost w-full flex items-center justify-center gap-1.5">
        <X size={13} /> Cancel
      </button>
    </div>
  )
}
