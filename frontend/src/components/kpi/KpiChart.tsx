import { useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'
import type { KpiEntry } from '../../types'

interface Props {
  entries: KpiEntry[]
}

type Range = '7d' | '30d' | '90d' | 'all'

function filterByRange(entries: KpiEntry[], range: Range): KpiEntry[] {
  if (range === 'all') return entries
  const days = range === '7d' ? 7 : range === '30d' ? 30 : 90
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - days)
  const cutoffStr = cutoff.toISOString().slice(0, 10)
  return entries.filter(e => e.date >= cutoffStr)
}

export default function KpiChart({ entries }: Props) {
  const metrics = [...new Set(entries.map(e => e.metric))]
  const [metric, setMetric] = useState(metrics[0] ?? '')
  const [range,  setRange]  = useState<Range>('30d')

  const metricEntries = filterByRange(
    entries.filter(e => e.metric === metric).sort((a, b) => a.date.localeCompare(b.date)),
    range,
  )

  const chartData = metricEntries.map(e => ({ date: e.date.slice(5), value: e.value }))
  const avg = metricEntries.length
    ? metricEntries.reduce((s, e) => s + e.value, 0) / metricEntries.length
    : 0
  const prev = entries.filter(e => e.metric === metric && !metricEntries.includes(e))
  const prevAvg = prev.length ? prev.reduce((s, e) => s + e.value, 0) / prev.length : 0
  const delta = prevAvg > 0 ? ((avg - prevAvg) / prevAvg) * 100 : null

  if (entries.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-600 text-sm">
        Log your first KPI entry to see the chart
      </div>
    )
  }

  return (
    <div className="flex-1 p-5 overflow-y-auto flex flex-col gap-4">
      <div className="flex items-center gap-3 flex-wrap">
        <select
          className="input-base text-xs flex-1 min-w-0"
          value={metric} onChange={e => setMetric(e.target.value)}
        >
          {metrics.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        <div className="flex gap-1">
          {(['7d','30d','90d','all'] as Range[]).map(r => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`px-2 py-1 rounded text-[11px] transition-all ${
                range === r
                  ? 'bg-analytics/10 text-analytics border border-analytics/30'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-secondary border border-white/5 rounded-lg p-4 flex-1 min-h-[200px]">
        {chartData.length < 2 ? (
          <p className="text-gray-600 text-xs text-center mt-8">Not enough data for this range</p>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 10 }} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} width={40} />
              <Tooltip
                contentStyle={{ background: '#161b22', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, fontSize: 12 }}
                labelStyle={{ color: '#e5e7eb' }}
              />
              <ReferenceLine y={avg} stroke="#fbbf24" strokeDasharray="4 4" />
              <Line type="monotone" dataKey="value" stroke="#fbbf24" strokeWidth={2} dot={{ r: 3, fill: '#fbbf24' }} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Avg / entry', value: avg.toLocaleString('vi-VN', { maximumFractionDigits: 1 }) },
          { label: 'vs prev period', value: delta != null ? `${delta > 0 ? '+' : ''}${delta.toFixed(1)}%` : '—' },
          { label: 'Entries', value: metricEntries.length },
        ].map(({ label, value }) => (
          <div key={label} className="bg-secondary border border-white/5 rounded-lg p-3 text-center">
            <p className="text-analytics text-base font-bold">{value}</p>
            <p className="text-gray-600 text-[10px] mt-0.5">{label}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
