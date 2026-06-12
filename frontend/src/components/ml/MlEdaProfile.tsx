import type { ProfileColumn } from '../../types'

export default function MlEdaProfile({ columns }: { columns: ProfileColumn[] }) {
  return (
    <div className="overflow-auto rounded-lg border border-data/20">
      <table className="w-full text-xs">
        <thead className="bg-data/10 text-gray-300">
          <tr>
            <th className="px-2 py-1.5 text-left">Cột</th>
            <th className="px-2 py-1.5 text-left">Loại</th>
            <th className="px-2 py-1.5 text-right">Null %</th>
            <th className="px-2 py-1.5 text-right">Cardinality</th>
            <th className="px-2 py-1.5 text-left">Mẫu</th>
          </tr>
        </thead>
        <tbody>
          {columns.map(c => (
            <tr key={c.name} className="border-t border-data/10">
              <td className="px-2 py-1.5 text-gray-200">{c.name}</td>
              <td className="px-2 py-1.5 text-gray-400">{c.role}</td>
              <td className={`px-2 py-1.5 text-right ${c.null_pct >= 20 ? 'text-amber-400' : 'text-gray-400'}`}>
                {c.null_pct}%
              </td>
              <td className="px-2 py-1.5 text-right text-gray-400">{c.cardinality}</td>
              <td className="px-2 py-1.5 text-gray-500 truncate max-w-[200px]">
                {c.samples.join(', ')}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
