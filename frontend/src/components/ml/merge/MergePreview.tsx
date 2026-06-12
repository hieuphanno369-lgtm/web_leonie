interface Props {
  rows: Record<string, string | null>[]
}

export default function MergePreview({ rows }: Props) {
  if (rows.length === 0) {
    return <p className="text-[11px] text-gray-600">Không có dòng nào để xem trước.</p>
  }
  const cols = Object.keys(rows[0])
  return (
    <div className="rounded-lg border border-white/5 overflow-auto max-h-72">
      <table className="w-full text-[11px]">
        <thead className="sticky top-0 bg-[#1a1a1a]">
          <tr>
            {cols.map(c => (
              <th key={c} className="text-left px-2.5 py-1.5 text-gray-400 font-medium border-b border-white/5">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-white/5">
              {cols.map(c => (
                <td key={c} className="px-2.5 py-1 text-gray-300 truncate max-w-[200px]">
                  {r[c] ?? <span className="text-gray-700">∅</span>}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
