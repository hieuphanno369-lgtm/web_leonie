import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import type { EdaDistribution } from '../../types'

export default function MlEdaDistribution({ dists }: { dists: EdaDistribution[] }) {
  if (dists.length === 0) return <p className="text-xs text-gray-500">Không có cột số để vẽ phân phối.</p>
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {dists.map(d => {
        const data = d.bins.map(b => ({ x: ((b.x0 + b.x1) / 2).toFixed(1), count: b.count }))
        return (
          <div key={d.column} className="rounded-lg border border-data/20 p-3">
            <div className="flex items-center justify-between mb-1">
              <p className="text-xs font-medium text-gray-200">{d.column}</p>
              <p className="text-[10px] text-gray-500">
                skew {d.skew}{d.log_applied ? ' · log' : ''} · median {d.median.toFixed(1)}
              </p>
            </div>
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={data}>
                <XAxis dataKey="x" tick={{ fontSize: 9, fill: '#9ca3af' }} interval={3} />
                <YAxis tick={{ fontSize: 9, fill: '#9ca3af' }} width={28} />
                <Tooltip contentStyle={{ fontSize: 11, background: '#111827', border: 'none' }} />
                <Bar dataKey="count" fill="#38bdf8" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )
      })}
    </div>
  )
}
