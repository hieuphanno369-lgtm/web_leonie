import { useEffect, useState, useCallback } from 'react'
import type { WIPItem } from '../../types'
import { fetchWIPs, deleteWIP } from '../../api/wip'
import WIPList   from '../../components/wip/WIPList'
import WIPDetail from '../../components/wip/WIPDetail'
import WIPForm   from '../../components/wip/WIPForm'
import { MSG } from '../../messages'

type PanelMode = 'empty' | 'detail' | 'create'

export default function WipBuilder() {
  const [wips,       setWips]       = useState<WIPItem[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [mode,       setMode]       = useState<PanelMode>('empty')
  const [apiError,   setApiError]   = useState('')

  const selected = wips.find(w => w.id === selectedId) ?? null

  const load = useCallback(async () => {
    try { setWips(await fetchWIPs()); setApiError('') }
    catch { setApiError(MSG.apiUnreachable) }
  }, [])

  useEffect(() => { load() }, [load])

  function handleSelect(id: string) { setSelectedId(id); setMode('detail') }

  function handleCreated(wip: WIPItem) {
    setWips(ws => [wip, ...ws])
    setSelectedId(wip.id)
    setMode('detail')
  }

  function handleProgressUpdate(updated: WIPItem) {
    setWips(ws => ws.map(w => w.id === updated.id ? updated : w))
  }

  async function handleDelete(id: string) {
    try {
      await deleteWIP(id)
      setWips(ws => ws.filter(w => w.id !== id))
      setSelectedId(null)
      setMode('empty')
    } catch { setApiError(MSG.deleteFailed) }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <WIPList
        wips={wips}
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
            <span className="text-3xl opacity-20">📋</span>
            <p>{MSG.emptySelectWip}</p>
          </div>
        )}
        {mode === 'detail' && selected && (
          <WIPDetail
            wip={selected}
            onProgressUpdate={handleProgressUpdate}
            onDelete={handleDelete}
          />
        )}
        {mode === 'create' && (
          <WIPForm
            onCreated={handleCreated}
            onCancel={() => setMode('empty')}
          />
        )}
      </div>
    </div>
  )
}
