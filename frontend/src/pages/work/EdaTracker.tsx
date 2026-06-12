import { useEffect, useState, useCallback } from 'react'
import type { EDARequest } from '../../types'
import { fetchEDA, createEDA, updateEDA, deleteEDA } from '../../api/eda'
import type { EDAPayload } from '../../api/eda'
import EDAList   from '../../components/eda/EDAList'
import EDADetail from '../../components/eda/EDADetail'
import EDAForm   from '../../components/eda/EDAForm'
import { MSG } from '../../messages'

type PanelMode = 'empty' | 'detail' | 'create' | 'edit'

export default function EdaTracker() {
  const [requests,   setRequests]   = useState<EDARequest[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [mode,       setMode]       = useState<PanelMode>('empty')
  const [apiError,   setApiError]   = useState('')

  const selected = requests.find(r => r.id === selectedId) ?? null

  const load = useCallback(async () => {
    try {
      setRequests(await fetchEDA())
      setApiError('')
    } catch {
      setApiError(MSG.apiUnreachable)
    }
  }, [])

  useEffect(() => { load() }, [load])

  function handleSelect(id: string) { setSelectedId(id); setMode('detail') }

  async function handleSave(payload: EDAPayload) {
    try {
      if (mode === 'create') {
        const created = await createEDA(payload)
        setRequests(rs => [created, ...rs])
        setSelectedId(created.id)
        setMode('detail')
      } else if (mode === 'edit' && selectedId) {
        const updated = await updateEDA(selectedId, payload)
        setRequests(rs => rs.map(r => r.id === selectedId ? updated : r))
        setMode('detail')
      }
    } catch {
      setApiError(MSG.saveFailed)
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteEDA(id)
      setRequests(rs => rs.filter(r => r.id !== id))
      setSelectedId(null)
      setMode('empty')
    } catch {
      setApiError(MSG.deleteFailed)
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <EDAList
        requests={requests}
        selectedId={selectedId}
        onSelect={handleSelect}
        onNew={() => { setSelectedId(null); setMode('create') }}
      />
      <div className="flex-1 flex overflow-hidden relative">
        {apiError && (
          <div className="absolute top-4 right-4 bg-danger/10 border border-danger/30 text-danger text-xs px-3 py-2 rounded-lg">
            {apiError}
          </div>
        )}
        {mode === 'empty' && (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-600 text-sm gap-2">
            <span className="text-3xl opacity-20">🔬</span>
            <p>{MSG.emptySelectEda}</p>
          </div>
        )}
        {mode === 'detail' && selected && (
          <EDADetail eda={selected} onEdit={() => setMode('edit')} onDelete={handleDelete} />
        )}
        {(mode === 'create' || mode === 'edit') && (
          <EDAForm
            initial={mode === 'edit' ? (selected ?? undefined) : undefined}
            onSave={handleSave}
            onCancel={() => setMode(selected ? 'detail' : 'empty')}
          />
        )}
      </div>
    </div>
  )
}
