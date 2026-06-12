import { useState } from 'react'
import { Download, FileWarning, FileDown, FileSpreadsheet, Code2 } from 'lucide-react'
import type { MergeSummary } from '../../../types'
import CodePanel from '../CodePanel'

interface Props {
  summary: MergeSummary
  code?: string
  onDownloadRejected: () => void
  onExport?: (fmt: 'csv' | 'xlsx') => void
}

function Metric({ label, value, hint, tone = 'default' }:
  { label: string; value: number; hint?: string; tone?: 'default' | 'good' | 'warn' }) {
  const color = tone === 'good' ? 'text-success' : tone === 'warn' ? 'text-amber-400' : 'text-white'
  return (
    <div className="rounded-lg bg-white/5 border border-white/5 px-3 py-2.5">
      <p className={`text-lg font-semibold ${color}`}>{value.toLocaleString('vi-VN')}</p>
      <p className="text-[11px] text-gray-400 leading-tight">{label}</p>
      {hint && <p className="text-[10px] text-gray-600 mt-0.5">{hint}</p>}
    </div>
  )
}

export default function MergeOutcome({ summary: s, code, onDownloadRejected, onExport }: Props) {
  const [showCode, setShowCode] = useState(false)
  const fill = Object.entries(s.per_field_fill_rate)
  const files = Object.entries(s.per_file_contribution)
  const maxContrib = Math.max(1, ...files.map(([, v]) => v))
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <Metric label="Tổng thu thập" value={s.total_raw} />
        <Metric label="Hợp lệ định dạng" value={s.valid_format} tone="good" />
        <Metric label="Null / sai" value={s.null_or_wrong} tone="warn" />
        <Metric label="Distinct" value={s.distinct} />
        <Metric label="Trùng đã loại (sạch)" value={s.dup_removed_clean} hint="hợp lệ − distinct" />
        <Metric label="Trùng đã loại (thô)" value={s.dup_removed_raw} hint="tổng − distinct" />
        <Metric label="Đủ thông tin" value={s.complete} tone="good" />
        <Metric label="Thiếu thông tin" value={s.incomplete} tone="warn" />
      </div>

      <div>
        <p className="text-[11px] uppercase tracking-wide text-gray-600 mb-1.5">Tỷ lệ điền theo cột</p>
        <div className="space-y-1">
          {fill.map(([col, rate]) => (
            <div key={col} className="flex items-center gap-2">
              <span className="text-[11px] text-gray-400 w-28 truncate">{col}</span>
              <div className="flex-1 h-2 rounded bg-white/5 overflow-hidden">
                <div className="h-full bg-data" style={{ width: `${Math.round(rate * 100)}%` }} />
              </div>
              <span className="text-[10px] text-gray-500 w-10 text-right">{Math.round(rate * 100)}%</span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <p className="text-[11px] uppercase tracking-wide text-gray-600 mb-1.5">Đóng góp theo file (dòng hợp lệ)</p>
        <div className="space-y-1">
          {files.map(([file, count]) => (
            <div key={file} className="flex items-center gap-2">
              <span className="text-[11px] text-gray-400 w-36 truncate" title={file}>{file}</span>
              <div className="flex-1 h-2 rounded bg-white/5 overflow-hidden">
                <div className="h-full bg-analytics" style={{ width: `${Math.round((count / maxContrib) * 100)}%` }} />
              </div>
              <span className="text-[10px] text-gray-500 w-12 text-right">{count.toLocaleString('vi-VN')}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {onExport && (
          <>
            <button onClick={() => onExport('csv')}
              className="flex items-center gap-1.5 rounded-md bg-success/10 border border-success/30 px-3 py-2 text-xs text-success hover:bg-success/20">
              <FileDown size={13} /> Xuất CSV
            </button>
            <button onClick={() => onExport('xlsx')}
              className="flex items-center gap-1.5 rounded-md bg-success/10 border border-success/30 px-3 py-2 text-xs text-success hover:bg-success/20">
              <FileSpreadsheet size={13} /> Xuất Excel
            </button>
          </>
        )}
        {s.rejected > 0 && (
          <button onClick={onDownloadRejected}
            className="flex items-center gap-1.5 rounded-md bg-white/5 border border-white/10 px-3 py-2 text-xs text-amber-400 hover:bg-white/10">
            <FileWarning size={13} /> Tải bản bị loại ({s.rejected.toLocaleString('vi-VN')} dòng)
            <Download size={12} />
          </button>
        )}
      </div>

      {code && (
        <div className="space-y-1.5">
          <button onClick={() => setShowCode(c => !c)}
            className="flex items-center gap-1.5 text-[11px] text-gray-500 hover:text-gray-300 transition-colors">
            <Code2 size={12} /> {showCode ? 'Ẩn code' : 'Show Code (toàn bộ pipeline)'}
          </button>
          {showCode && <CodePanel code={code} filename="combine_pipeline.py" defaultOpen />}
        </div>
      )}
    </div>
  )
}
