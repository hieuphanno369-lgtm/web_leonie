import { useState, useEffect } from 'react'
import { Check, X } from 'lucide-react'
import type { KpiCategory, KpiEntry } from '../../types'
import { fetchKpiMetrics, createKpi } from '../../api/kpi'
import { MSG } from '../../messages'

interface Props {
  onCreated: (entry: KpiEntry) => void
  onCancel: () => void
}

export default function KpiForm({ onCreated, onCancel }: Props) {
  const [metric,   setMetric]   = useState('')
  const [value,    setValue]    = useState('')
  const [date,     setDate]     = useState(new Date().toISOString().slice(0, 10))
  const [category, setCategory] = useState<KpiCategory>('da_output')
  const [note,     setNote]     = useState('')
  const [metrics,  setMetrics]  = useState<string[]>([])
  const [error,    setError]    = useState('')
  const [saving,   setSaving]   = useState(false)

  useEffect(() => {
    fetchKpiMetrics().then(setMetrics).catch(() => {})
  }, [])

  async function handleSubmit() {
    if (!metric.trim()) { setError(MSG.metricRequired); return }
    if (!value || isNaN(Number(value))) { setError(MSG.validNumberRequired); return }
    setError(''); setSaving(true)
    try {
      const entry = await createKpi({
        metric: metric.trim(), value: Number(value),
        date, category, note: note || null,
      })
      onCreated(entry)
    } catch { setError(MSG.saveFailed) }
    finally { setSaving(false) }
  }

  return (
    <div className="flex-1 p-5 overflow-y-auto">
      <h2 className="text-sm font-semibold text-white mb-4">Log KPI</h2>

      <div className="mb-3">
        <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Metric *</label>
        <input
          className="input-base" list="metrics-list"
          placeholder="Queries viết, GMV ColosBaby..."
          value={metric} onChange={e => setMetric(e.target.value)}
          autoFocus
        />
        <datalist id="metrics-list">
          {metrics.map(m => <option key={m} value={m} />)}
        </datalist>
      </div>

      <div className="flex gap-3 mb-3">
        <div className="flex-1">
          <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Value *</label>
          <input className="input-base" type="number" placeholder="0" value={value} onChange={e => setValue(e.target.value)} />
        </div>
        <div className="flex-1">
          <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Date</label>
          <input className="input-base" type="date" value={date} onChange={e => setDate(e.target.value)} />
        </div>
      </div>

      <div className="mb-3">
        <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Category</label>
        <select className="input-base" value={category} onChange={e => setCategory(e.target.value as KpiCategory)}>
          <option value="da_output">DA Output</option>
          <option value="business">Business</option>
        </select>
      </div>

      <div className="mb-4">
        <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Note</label>
        <input className="input-base" placeholder="Không bắt buộc..." value={note} onChange={e => setNote(e.target.value)} />
      </div>

      {error && <p className="text-danger text-xs mb-3">{error}</p>}

      <button onClick={handleSubmit} disabled={saving} className="btn-primary w-full mb-2 flex items-center justify-center gap-1.5 disabled:opacity-50">
        <Check size={13} /> {saving ? 'Saving...' : 'Save Entry'}
      </button>
      <button onClick={onCancel} className="btn-ghost w-full flex items-center justify-center gap-1.5">
        <X size={13} /> Cancel
      </button>
    </div>
  )
}
