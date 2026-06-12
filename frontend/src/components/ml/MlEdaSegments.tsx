import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import type { EdaReport } from '../../types'

export default function MlEdaSegments({ segments }: { segments: EdaReport['segments'] }) {
  const { table, scatter } = segments
  if (table.length === 0) return <p className="text-xs text-gray-500">Không có cột nhóm (dimension) để phân tích.</p>
  const metricKeys = Object.keys(table[0]).filter(k => k !== 'segment' && k !== 'count')
  return (
    <div className="space-y-4">
      <div className="overflow-auto rounded-lg border border-data/20">
        <table className="w-full text-xs">
          <thead className="bg-data/10 text-gray-300">
            <tr>
              <th className="px-2 py-1.5 text-left">Nhóm</th>
              <th className="px-2 py-1.5 text-right">Số dòng</th>
              {metricKeys.map(k => <th key={k} className="px-2 py-1.5 text-right">{k}</th>)}
            </tr>
          </thead>
          <tbody>
            {table.map(r => (
              <tr key={r.segment} className="border-t border-data/10">
                <td className="px-2 py-1.5 text-gray-200">{r.segment}</td>
                <td className="px-2 py-1.5 text-right text-gray-400">{r.count}</td>
                {metricKeys.map(k => (
                  <td key={k} className="px-2 py-1.5 text-right text-gray-400">
                    {typeof r[k] === 'number' ? (r[k] as number).toLocaleString() : r[k]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {scatter.x_col && scatter.y_col && scatter.points.length > 0 && (
        <div className="rounded-lg border border-data/20 p-3">
          <p className="text-xs font-medium text-gray-200 mb-1">
            {scatter.x_col} vs {scatter.y_col}
          </p>
          <ResponsiveContainer width="100%" height={220}>
            <ScatterChart>
              <XAxis type="number" dataKey="x" name={scatter.x_col}
                tick={{ fontSize: 9, fill: '#9ca3af' }} />
              <YAxis type="number" dataKey="y" name={scatter.y_col}
                tick={{ fontSize: 9, fill: '#9ca3af' }} width={36} />
              <Tooltip contentStyle={{ fontSize: 11, background: '#111827', border: 'none' }} />
              <Scatter data={scatter.points} fill="#38bdf8" fillOpacity={0.5} />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
