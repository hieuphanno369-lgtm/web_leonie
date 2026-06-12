import { useEffect, useState } from 'react'
import { ChevronDown, ChevronRight, Code2 } from 'lucide-react'
import type { DatasetInfo } from '../../types'
import { fetchDescribe, type DescribeRow } from '../../api/ml'
import MlSqlEditor from './MlSqlEditor'
import CodePanel from './CodePanel'
import { MSG } from '../../messages'

interface Props {
  dataset: DatasetInfo
  running: boolean
  sqlError: string
  onRun: (sql: string) => void
}

function fmt(v: number | undefined) {
  if (v === undefined) return '—'
  return v.toLocaleString('vi-VN', { maximumFractionDigits: 3 })
}

export default function MlDescribePanel({ dataset, running, sqlError, onRun }: Props) {
  const [rows,     setRows]     = useState<DescribeRow[]>([])
  const [code,     setCode]     = useState('')
  const [open,     setOpen]     = useState(true)
  const [loading,  setLoading]  = useState(false)
  const [showCode, setShowCode] = useState(false)

  useEffect(() => {
    setLoading(true)
    fetchDescribe(dataset.file_id)
      .then(res => { setRows(res.rows); setCode(res.code) })
      .catch(() => { setRows([]); setCode('') })
      .finally(() => setLoading(false))
  }, [dataset.file_id])

  return (
    <div className="border border-white/5 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-3 py-2 bg-white/3 hover:bg-white/5 transition-colors"
      >
        <span className="text-[11px] font-medium text-gray-300">Dataset Overview</span>
        <span className="text-gray-600">
          {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
      </button>

      {open && (
        <>
          <div className="overflow-x-auto">
            {loading ? (
              <p className="text-[10px] text-gray-600 px-3 py-2">{MSG.loading}</p>
            ) : (
              <table className="w-full text-[10px]">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="text-left  px-2 py-1.5 text-gray-600 font-normal">Column</th>
                    <th className="text-left  px-2 py-1.5 text-gray-600 font-normal">Type</th>
                    <th className="text-right px-2 py-1.5 text-gray-600 font-normal">Nulls%</th>
                    <th className="text-right px-2 py-1.5 text-gray-600 font-normal">Min</th>
                    <th className="text-right px-2 py-1.5 text-gray-600 font-normal">Max</th>
                    <th className="text-right px-2 py-1.5 text-gray-600 font-normal">Mean</th>
                    <th className="text-right px-2 py-1.5 text-gray-600 font-normal">Median</th>
                    <th className="text-right px-2 py-1.5 text-gray-600 font-normal">Range</th>
                    <th className="text-right px-2 py-1.5 text-gray-600 font-normal">Std</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map(r => (
                    <tr key={r.col} className="border-b border-white/3 hover:bg-white/2">
                      <td className="px-2 py-1 text-gray-300 max-w-[80px] truncate" title={r.col}>{r.col}</td>
                      <td className="px-2 py-1 text-gray-600">{r.dtype.replace('DataType.', '')}</td>
                      <td className={`px-2 py-1 text-right ${r.nulls > 20 ? 'text-danger' : r.nulls > 5 ? 'text-yellow-500' : 'text-gray-500'}`}>
                        {r.nulls}%
                      </td>
                      <td className="px-2 py-1 text-right text-gray-500">{fmt(r.min)}</td>
                      <td className="px-2 py-1 text-right text-gray-500">{fmt(r.max)}</td>
                      <td className="px-2 py-1 text-right text-gray-400">{fmt(r.mean)}</td>
                      <td className="px-2 py-1 text-right text-gray-400">{fmt(r.median)}</td>
                      <td className="px-2 py-1 text-right text-gray-500">{fmt(r.range)}</td>
                      <td className="px-2 py-1 text-right text-gray-500">{fmt(r.std)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {code && (
            <div className="px-2 pt-1 pb-2 space-y-1.5">
              <button
                onClick={() => setShowCode(s => !s)}
                className="flex items-center gap-1.5 text-[10px] text-gray-500 hover:text-gray-300 transition-colors"
              >
                <Code2 size={11} /> {showCode ? 'Ẩn code' : 'Show Code'}
              </button>
              {showCode && <CodePanel code={code} filename="describe_overview.py" defaultOpen />}
            </div>
          )}
        </>
      )}

      {/* Quick run controls — sits flush at the bottom of this card */}
      <MlSqlEditor
        disabled={false}
        running={running}
        error={sqlError}
        onRun={onRun}
      />
    </div>
  )
}
