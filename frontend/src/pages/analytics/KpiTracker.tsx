import { useEffect, useState, useCallback } from 'react'
import type { KpiEntry } from '../../types'
import { fetchKpi, deleteKpi } from '../../api/kpi'
import KpiList  from '../../components/kpi/KpiList'
import KpiForm  from '../../components/kpi/KpiForm'
import KpiChart from '../../components/kpi/KpiChart'
import { MSG } from '../../messages'

type Panel = 'chart' | 'form'

export default function KpiTracker() {
  const [entries,    setEntries]    = useState<KpiEntry[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [panel,      setPanel]      = useState<Panel>('chart')
  const [apiError,   setApiError]   = useState('')

  const load = useCallback(async () => {
    try { setEntries(await fetchKpi()); setApiError('') }
    catch { setApiError(MSG.apiUnreachable) }
  }, [])

  useEffect(() => { load() }, [load])

  async function handleDelete(id: string) {
    try {
      await deleteKpi(id)
      setEntries(es => es.filter(e => e.id !== id))
      if (selectedId === id) setSelectedId(null)
    } catch { setApiError(MSG.deleteFailed) }
  }

  function handleCreated(entry: KpiEntry) {
    setEntries(es => [entry, ...es])
    setSelectedId(entry.id)
    setPanel('chart')
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <KpiList
        entries={entries}
        selectedId={selectedId}
        onSelect={id => { setSelectedId(id); setPanel('chart') }}
        onDelete={handleDelete}
        onNew={() => setPanel('form')}
      />
      <div className="flex-1 flex overflow-hidden relative">
        {apiError && (
          <div className="absolute top-4 right-4 bg-danger/10 border border-danger/30 text-danger text-xs px-3 py-2 rounded-lg z-10">
            {apiError}
          </div>
        )}
        {panel === 'form' ? (
          <KpiForm onCreated={handleCreated} onCancel={() => setPanel('chart')} />
        ) : (
          <KpiChart entries={entries} />
        )}
      </div>
    </div>
  )
}
