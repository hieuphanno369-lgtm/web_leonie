import type { PreviewResult } from '../../types'

interface Props {
  data: PreviewResult
}

export default function PreviewPanel({ data }: Props) {
  if (data.columns.length === 0) {
    return <p className="text-gray-500 text-xs p-3">Preview returned no columns.</p>
  }
  return (
    <div className="glass-card overflow-hidden">
      <div className="px-3 py-2 border-b border-white/5 text-[11px] text-gray-400">
        Preview · {data.rows.length} rows × {data.columns.length} cols
      </div>
      <div className="overflow-auto max-h-80">
        <table className="w-full text-[11px] border-collapse">
          <thead className="sticky top-0 bg-tertiary">
            <tr>
              {data.columns.map(c => (
                <th key={c} className="text-left px-2 py-1.5 text-gray-400 font-medium border-b border-white/5 whitespace-nowrap">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, i) => (
              <tr key={i} className="hover:bg-white/5">
                {row.map((cell, j) => (
                  <td key={j} className="px-2 py-1 text-gray-300 border-b border-white/5 whitespace-nowrap max-w-xs truncate">
                    {cell == null ? <span className="text-gray-600">null</span> : String(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
