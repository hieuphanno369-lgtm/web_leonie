import { useEffect, useState, useCallback } from 'react'
import type { ActionPlan } from '../../types'
import { fetchPlans, createPlan, updatePlan, deletePlan } from '../../api/action_plan'
import type { APPayload } from '../../api/action_plan'
import APList   from '../../components/action_plan/APList'
import APDetail from '../../components/action_plan/APDetail'
import APForm   from '../../components/action_plan/APForm'
import { MSG } from '../../messages'

type PanelMode = 'empty' | 'detail' | 'create' | 'edit'

export default function ActionPlan() {
  const [plans,      setPlans]      = useState<ActionPlan[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [mode,       setMode]       = useState<PanelMode>('empty')
  const [apiError,   setApiError]   = useState('')

  const selected = plans.find(p => p.id === selectedId) ?? null

  const load = useCallback(async () => {
    try {
      setPlans(await fetchPlans())
      setApiError('')
    } catch {
      setApiError(MSG.apiUnreachable)
    }
  }, [])

  useEffect(() => { load() }, [load])

  function handleSelect(id: string) { setSelectedId(id); setMode('detail') }

  async function handleSave(payload: APPayload) {
    try {
      if (mode === 'create') {
        const created = await createPlan(payload)
        setPlans(ps => [created, ...ps])
        setSelectedId(created.id)
        setMode('detail')
      } else if (mode === 'edit' && selectedId) {
        const updated = await updatePlan(selectedId, payload)
        setPlans(ps => ps.map(p => p.id === selectedId ? updated : p))
        setMode('detail')
      }
    } catch {
      setApiError(MSG.saveFailed)
    }
  }

  async function handleDelete(id: string) {
    try {
      await deletePlan(id)
      setPlans(ps => ps.filter(p => p.id !== id))
      setSelectedId(null)
      setMode('empty')
    } catch {
      setApiError(MSG.deleteFailed)
    }
  }

  function handleUpdated(updated: ActionPlan) {
    setPlans(ps => ps.map(p => p.id === updated.id ? updated : p))
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <APList
        plans={plans}
        selectedId={selectedId}
        onSelect={handleSelect}
        onNew={() => { setSelectedId(null); setMode('create') }}
      />
      <div className="flex-1 flex overflow-hidden relative">
        {apiError && (
          <div className="absolute top-4 right-4 bg-danger/10 border border-danger/30 text-danger text-xs px-3 py-2 rounded-lg z-10">
            {apiError}
          </div>
        )}
        {mode === 'empty' && (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-600 text-sm gap-2">
            <span className="text-3xl opacity-20">📋</span>
            <p>{MSG.emptySelectPlan}</p>
            <p className="text-[11px] text-gray-700">AI sẽ generate timeline, checklist, input/output sau khi bạn nhập</p>
          </div>
        )}
        {mode === 'detail' && selected && (
          <APDetail
            plan={selected}
            onEdit={() => setMode('edit')}
            onDelete={handleDelete}
            onUpdated={handleUpdated}
          />
        )}
        {(mode === 'create' || mode === 'edit') && (
          <APForm
            initial={mode === 'edit' ? (selected ?? undefined) : undefined}
            onSave={handleSave}
            onCancel={() => setMode(selected ? 'detail' : 'empty')}
          />
        )}
      </div>
    </div>
  )
}
