import { useState } from 'react'
import { Copy, Download, Check } from 'lucide-react'
import type { QueryResult } from '../../types'
import { copyRowsAsCsv, downloadCsv } from './chartExport'

interface Props { result: QueryResult }

export default function MlTableView({ result }: Props) {
  const display = result.rows.slice(0, 500)
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    const ok = await copyRowsAsCsv(result.columns, result.rows)
    if (ok) { setCopied(true); setTimeout(() => setCopied(false), 1500) }
  }

  return (
    <div className="p-4 overflow-auto h-full">
      <div className="flex items-center justify-between mb-2">
        <p className="text-gray-600 text-[10px]">
          {result.rows.length} rows · {result.duration_ms.toFixed(1)}ms
          {result.rows.length > 500 && ' · showing first 500'}
        </p>
        <div className="flex items-center gap-2">
          <button onClick={handleCopy}
            className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-300 transition-colors">
            {copied ? <Check size={11} className="text-green-400" /> : <Copy size={11} />}
            {copied ? 'Copied!' : 'Copy CSV'}
          </button>
          <button onClick={() => downloadCsv(result.columns, result.rows, 'ml_result.csv')}
            className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-300 transition-colors">
            <Download size={11} /> CSV
          </button>
        </div>
      </div>
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr>
            {result.columns.map(c => (
              <th key={c} className="text-left text-[10px] text-gray-500 uppercase tracking-wider px-3 py-1.5 border-b border-white/5 whitespace-nowrap">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {display.map((row, i) => (
            <tr key={i} className="hover:bg-white/3 transition-colors">
              {row.map((cell, j) => (
                <td key={j} className="px-3 py-1.5 text-gray-300 border-b border-white/3 whitespace-nowrap max-w-[200px] truncate">
                  {cell == null ? <span className="text-gray-600 italic">null</span> : String(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
