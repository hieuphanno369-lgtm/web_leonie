import { useState, useEffect, useCallback } from 'react'
import { Trash2, Plus } from 'lucide-react'
import type { WIPItem, WIPLog } from '../../types'
import { updateWIPProgress, fetchLogs, addLog, deleteLog } from '../../api/wip'
import { MSG } from '../../messages'

interface Props {
  wip: WIPItem
  onProgressUpdate: (updated: WIPItem) => void
  onDelete: (id: string) => void
}

function progressColor(p: number) {
  if (p >= 100) return 'accent-work'
  if (p >= 70)  return 'accent-warning'
  return 'accent-data'
}

function progressBarColor(p: number) {
  if (p >= 100) return 'bg-work'
  if (p >= 70)  return 'bg-warning'
  return 'bg-data'
}

export default function WIPDetail({ wip, onProgressUpdate, onDelete }: Props) {
  const [logs,          setLogs]          = useState<WIPLog[]>([])
  const [localProgress, setLocalProgress] = useState(wip.progress)
  const [showLogInput,  setShowLogInput]  = useState(false)
  const [logDate,       setLogDate]       = useState(new Date().toISOString().slice(0, 10))
  const [logNote,       setLogNote]       = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [saving,        setSaving]        = useState(false)
  const [error,         setError]         = useState('')

  useEffect(() => {
    setLocalProgress(wip.progress)
    setConfirmDelete(false)
    setShowLogInput(false)
  }, [wip.id, wip.progress])

  const loadLogs = useCallback(async () => {
    try { setLogs(await fetchLogs(wip.id)) } catch { /* ignore */ }
  }, [wip.id])

  useEffect(() => { loadLogs() }, [loadLogs])

  async function handleSliderRelease() {
    try {
      const updated = await updateWIPProgress(wip.id, localProgress)
      onProgressUpdate(updated)
    } catch {
      setError(MSG.updateProgressFailed)
    }
  }

  async function handleAddLog() {
    if (!logNote.trim()) return
    setSaving(true)
    try {
      const log = await addLog(wip.id, logDate, logNote.trim())
      setLogs(ls => [log, ...ls])
      setLogNote('')
      setShowLogInput(false)
    } catch {
      setError(MSG.addLogFailed)
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteLog(log_id: string) {
    try {
      await deleteLog(wip.id, log_id)
      setLogs(ls => ls.filter(l => l.id !== log_id))
    } catch {
      setError(MSG.deleteLogFailed)
    }
  }

  const fmtDate = (iso: string) =>
    new Date(iso + 'T00:00:00').toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' })

  return (
    <div className="flex-1 p-5 overflow-y-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <h2 className="text-base font-semibold text-white leading-snug">{wip.task_title}</h2>
        {confirmDelete ? (
          <button onClick={() => onDelete(wip.id)} className="btn-danger flex items-center gap-1 text-xs px-2.5 py-1 flex-shrink-0">
            <Trash2 size={12} /> Confirm
          </button>
        ) : (
          <button
            onClick={() => setConfirmDelete(true)}
            className="btn-ghost flex items-center gap-1 text-xs px-2.5 py-1 hover:text-danger hover:border-danger/30 flex-shrink-0"
          >
            <Trash2 size={12} />
          </button>
        )}
      </div>

      {/* Progress */}
      <div className="mb-5">
        <div className="flex items-center justify-between mb-2">
          <p className="text-[10px] uppercase tracking-widest text-gray-600">Progress</p>
          <span className={`text-sm font-bold tabular-nums ${progressBarColor(localProgress).replace('bg-', 'text-')}`}>
            {localProgress}%
          </span>
        </div>
        <div className="h-2 bg-white/5 rounded-full overflow-hidden mb-2">
          <div
            className={`h-full rounded-full transition-all ${progressBarColor(localProgress)}`}
            style={{ width: `${localProgress}%` }}
          />
        </div>
        <input
          type="range"
          min={0} max={100}
          value={localProgress}
          className={`w-full h-1.5 rounded-full appearance-none cursor-pointer bg-white/5 ${progressColor(localProgress)}`}
          onChange={e => setLocalProgress(Number(e.target.value))}
          onMouseUp={handleSliderRelease}
          onTouchEnd={handleSliderRelease}
        />
      </div>

      <hr className="border-white/5 mb-4" />

      {/* Log section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <p className="text-[10px] uppercase tracking-widest text-gray-600">Daily Log</p>
          <button
            onClick={() => setShowLogInput(v => !v)}
            className="btn-ghost flex items-center gap-1 text-xs px-2 py-1"
          >
            <Plus size={11} /> Add
          </button>
        </div>

        {showLogInput && (
          <div className="bg-secondary border border-white/8 rounded-lg p-3 mb-3">
            <div className="flex gap-2 mb-2">
              <input
                type="date"
                className="input-base text-xs w-36"
                value={logDate}
                onChange={e => setLogDate(e.target.value)}
              />
            </div>
            <textarea
              className="input-base resize-none text-xs w-full mb-2"
              rows={2}
              placeholder="Hôm nay bạn đã làm gì?"
              value={logNote}
              onChange={e => setLogNote(e.target.value)}
              autoFocus
            />
            <div className="flex gap-2">
              <button onClick={handleAddLog} disabled={saving} className="btn-primary text-xs px-3 py-1 disabled:opacity-50">
                {saving ? 'Saving...' : 'Save'}
              </button>
              <button onClick={() => setShowLogInput(false)} className="btn-ghost text-xs px-3 py-1">Cancel</button>
            </div>
          </div>
        )}

        {error && <p className="text-danger text-xs mb-2">{error}</p>}

        {logs.length === 0 ? (
          <p className="text-gray-600 text-xs italic">{MSG.emptyLogs}</p>
        ) : (
          <div className="flex flex-col gap-2">
            {logs.map(log => (
              <div key={log.id} className="flex gap-3 group">
                <span className="text-[11px] text-gray-500 tabular-nums flex-shrink-0 pt-0.5">
                  {fmtDate(log.date)}
                </span>
                <p className="text-xs text-gray-300 flex-1 leading-relaxed">{log.note}</p>
                <button
                  onClick={() => handleDeleteLog(log.id)}
                  className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-danger transition-opacity flex-shrink-0"
                >
                  <Trash2 size={11} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
