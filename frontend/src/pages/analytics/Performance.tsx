import { useEffect, useState, useCallback } from 'react'
import type { PerformanceSummary, StreakRule } from '../../types'
import { fetchPerformanceSummary, fetchStreakRule, saveStreakRule } from '../../api/performance'
import StreakCard      from '../../components/performance/StreakCard'
import RuleEditor      from '../../components/performance/RuleEditor'
import OutputGrid      from '../../components/performance/OutputGrid'
import CalendarHeatmap from '../../components/performance/CalendarHeatmap'
import { MSG } from '../../messages'

export default function Performance() {
  const [summary,     setSummary]     = useState<PerformanceSummary | null>(null)
  const [rule,        setRule]        = useState<StreakRule | null>(null)
  const [editingRule, setEditingRule] = useState(false)
  const [apiError,    setApiError]    = useState('')

  const load = useCallback(async () => {
    try {
      const [s, r] = await Promise.all([fetchPerformanceSummary(), fetchStreakRule()])
      setSummary(s)
      setRule(r.streak_rule)
      setApiError('')
    } catch { setApiError(MSG.apiUnreachable) }
  }, [])

  useEffect(() => { load() }, [load])

  async function handleSaveRule(newRule: StreakRule) {
    try {
      await saveStreakRule(newRule)
      setRule(newRule)
      setEditingRule(false)
      await load()
    } catch { setApiError(MSG.saveRuleFailed) }
  }

  if (!summary || !rule) {
    return (
      <div className="flex-1 flex items-center justify-center">
        {apiError
          ? <p className="text-danger text-sm">{apiError}</p>
          : <div className="w-6 h-6 border-2 border-analytics/30 border-t-analytics rounded-full animate-spin" />}
      </div>
    )
  }

  return (
    <div className="p-5 max-w-2xl">
      <h1 className="text-base font-semibold text-white mb-5">Performance</h1>

      {apiError && (
        <div className="bg-danger/10 border border-danger/30 text-danger text-xs px-3 py-2 rounded-lg mb-4">
          {apiError}
        </div>
      )}

      <div className="flex gap-4 mb-5 items-start">
        <StreakCard streak={summary.streak} rule={rule} onEditRule={() => setEditingRule(v => !v)} />
        <div className="flex-1 flex flex-col gap-3">
          {editingRule && (
            <RuleEditor rule={rule} onSave={handleSaveRule} onCancel={() => setEditingRule(false)} />
          )}
          {!editingRule && <OutputGrid summary={summary} />}
        </div>
      </div>

      <CalendarHeatmap calendar={summary.calendar} />
    </div>
  )
}
