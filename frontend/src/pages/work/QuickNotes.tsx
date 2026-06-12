import { useEffect, useState, useCallback } from 'react'
import type { QuickNote, Task, EDARequest } from '../../types'
import { fetchNotes, deleteNote } from '../../api/notes'
import { fetchTasks } from '../../api/tasks'
import { fetchEDA } from '../../api/eda'
import NoteList   from '../../components/notes/NoteList'
import NoteDetail from '../../components/notes/NoteDetail'
import NoteForm   from '../../components/notes/NoteForm'
import { MSG } from '../../messages'

type PanelMode = 'empty' | 'detail' | 'create' | 'edit'

export default function QuickNotes() {
  const [notes,      setNotes]      = useState<QuickNote[]>([])
  const [tasks,      setTasks]      = useState<Task[]>([])
  const [edas,       setEdas]       = useState<EDARequest[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [mode,       setMode]       = useState<PanelMode>('empty')
  const [apiError,   setApiError]   = useState('')

  const [dateFrom,   setDateFrom]   = useState('')
  const [dateTo,     setDateTo]     = useState('')
  const [category,   setCategory]   = useState('')

  const selected = notes.find(n => n.id === selectedId) ?? null

  const load = useCallback(async () => {
    try {
      const [n, t, e] = await Promise.all([
        fetchNotes({ date_from: dateFrom, date_to: dateTo, category }),
        fetchTasks(),
        fetchEDA(),
      ])
      setNotes(n)
      setTasks(t)
      setEdas(e)
      setApiError('')
    } catch {
      setApiError(MSG.apiUnreachable)
    }
  }, [dateFrom, dateTo, category])

  useEffect(() => { load() }, [load])

  function handleSelect(id: string) {
    setSelectedId(id)
    setMode('detail')
  }

  function handleSaved(note: QuickNote) {
    setNotes(ns =>
      ns.some(n => n.id === note.id)
        ? ns.map(n => n.id === note.id ? note : n)
        : [note, ...ns]
    )
    setSelectedId(note.id)
    setMode('detail')
  }

  async function handleDelete(id: string) {
    try {
      await deleteNote(id)
      setNotes(ns => ns.filter(n => n.id !== id))
      setSelectedId(null)
      setMode('empty')
    } catch {
      setApiError(MSG.deleteFailed)
    }
  }

  const taskTitle = selected?.task_id
    ? (tasks.find(t => t.id === selected.task_id)?.title ?? null)
    : null
  const edaTitle = selected?.eda_id
    ? (edas.find(e => e.id === selected.eda_id)?.title ?? null)
    : null

  return (
    <div className="flex h-screen overflow-hidden">
      <NoteList
        notes={notes}
        selectedId={selectedId}
        dateFrom={dateFrom}
        dateTo={dateTo}
        category={category}
        onSelect={handleSelect}
        onNew={() => { setSelectedId(null); setMode('create') }}
        onDateFromChange={v => { setDateFrom(v); setSelectedId(null); setMode('empty') }}
        onDateToChange={v => { setDateTo(v);   setSelectedId(null); setMode('empty') }}
        onCategoryChange={v => { setCategory(v); setSelectedId(null); setMode('empty') }}
      />

      <div className="flex-1 flex overflow-hidden relative">
        {apiError && (
          <div className="absolute top-4 right-4 bg-danger/10 border border-danger/30 text-danger text-xs px-3 py-2 rounded-lg z-10">
            {apiError}
          </div>
        )}

        {mode === 'empty' && (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-600 text-sm gap-2">
            <span className="text-3xl opacity-20">📝</span>
            <p>{MSG.emptySelectNote}</p>
          </div>
        )}

        {mode === 'detail' && selected && (
          <NoteDetail
            note={selected}
            taskTitle={taskTitle}
            edaTitle={edaTitle}
            onEdit={() => setMode('edit')}
            onDelete={handleDelete}
          />
        )}

        {(mode === 'create' || mode === 'edit') && (
          <NoteForm
            initial={mode === 'edit' ? selected : null}
            tasks={tasks}
            edas={edas}
            onSaved={handleSaved}
            onCancel={() => setMode(selected ? 'detail' : 'empty')}
          />
        )}
      </div>
    </div>
  )
}
