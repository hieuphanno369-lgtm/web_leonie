import { useState } from 'react'
import { AlertTriangle, AlertCircle, CheckCircle, Download } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Cell,
} from 'recharts'
import type { ZScoreData } from '../../types'
import { downloadZScoreCsv } from '../../api/ml'

interface Props {
  data:   ZScoreData
  colA:   string
  fileId: string
}

const PRESETS = [1.5, 2.0, 2.5, 3.0]

type Status = 'outlier' | 'watch' | 'normal'

export default function ZScoreResult({ data, colA, fileId }: Props) {
  const [threshold,   setThreshold]   = useState(2.0)
  const [downloading, setDownloading] = useState(false)

  function statusOf(z: number): Status {
    const az = Math.abs(z)
    if (az >= threshold) return 'outlier'
    if (az >= 1)         return 'watch'
    return 'normal'
  }

  function barFill(x0: number, x1: number): string {
    const c = (x0 + x1) / 2
    if (Math.abs(c) >= threshold) return '#ef4444'
    if (Math.abs(c) >= 1)         return '#f59e0b'
    return '#34d399'
  }

  async function handleDownload() {
    setDownloading(true)
    try { await downloadZScoreCsv(fileId, colA) }
    finally { setDownloading(false) }
  }

  const outliers     = data.rows.filter(r => Math.abs(r.z_score) >= threshold)
  const outlierCount = outliers.length
  const outlierPct   = data.n > 0
    ? ((outlierCount / data.n) * 100).toFixed(2)
    : '0.00'

  const STATUS_STYLE: Record<Status, { cls: string; Icon: typeof AlertTriangle; label: string }> = {
    outlier: { cls: 'text-danger',     Icon: AlertTriangle, label: 'Outlier' },
    watch:   { cls: 'text-yellow-400', Icon: AlertCircle,   label: 'Watch'   },
    normal:  { cls: 'text-work',       Icon: CheckCircle,   label: 'Normal'  },
  }

  return (
    <div className="flex flex-col gap-4">

      {/* ── Summary ── */}
      <div className="bg-secondary border border-white/5 rounded-lg p-4">
        <div className="grid grid-cols-3 gap-3">
          {(['mean', 'std', 'n'] as const).map(key => (
            <div key={key}>
              <p className="text-[10px] text-gray-600 uppercase tracking-wider">{key}</p>
              <p className="text-sm font-semibold text-white">
                {(data[key] as number).toLocaleString('vi-VN', { maximumFractionDigits: 4 })}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Threshold control ── */}
      <div className="bg-secondary border border-white/5 rounded-lg p-4 flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-gray-600 uppercase tracking-wider whitespace-nowrap">
            Ngưỡng outlier
          </span>
          <input
            type="range" min={1} max={4} step={0.1}
            value={threshold}
            onChange={e => setThreshold(parseFloat(e.target.value))}
            className="flex-1 accent-analytics h-1"
          />
          <span className="text-sm font-semibold text-analytics w-8 text-right">
            {threshold.toFixed(1)}
          </span>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] text-gray-600">Preset:</span>
          {PRESETS.map(p => (
            <button
              key={p}
              onClick={() => setThreshold(p)}
              className={`px-2 py-0.5 rounded text-[10px] border transition-all ${
                threshold === p
                  ? 'bg-analytics/10 text-analytics border-analytics/30'
                  : 'text-gray-500 border-transparent hover:text-gray-300'
              }`}
            >
              {p}
            </button>
          ))}
          <span className={`ml-auto text-[11px] font-medium ${
            outlierCount > 0 ? 'text-danger' : 'text-work'
          }`}>
            → {outlierCount} outliers ({outlierPct}%)
          </span>
        </div>
      </div>

      {/* ── Histogram ── */}
      <div className="bg-secondary border border-white/5 rounded-lg p-4">
        <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-2">
          Phân phối Z-Score
        </p>
        <div style={{ height: 160 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data.histogram_bins}
              margin={{ top: 4, right: 8, bottom: 4, left: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="x0"
                type="number"
                domain={[
                  data.histogram_bins[0]?.x0 ?? -4,
                  data.histogram_bins[data.histogram_bins.length - 1]?.x1 ?? 4,
                ]}
                tick={{ fill: '#6b7280', fontSize: 9 }}
                tickFormatter={v => Number(v).toFixed(1)}
              />
              <YAxis tick={{ fill: '#6b7280', fontSize: 9 }} width={32} />
              <Tooltip
                contentStyle={{
                  background: '#161b22',
                  border: '1px solid rgba(255,255,255,0.1)',
                  fontSize: 11,
                }}
                formatter={(v) => [+(v ?? 0), 'count']}
                labelFormatter={(x0) => `z ≈ ${Number(x0).toFixed(2)}`}
              />
              <ReferenceLine
                x={threshold}
                stroke="rgba(239,68,68,0.5)"
                strokeDasharray="4 2"
              />
              <ReferenceLine
                x={-threshold}
                stroke="rgba(239,68,68,0.5)"
                strokeDasharray="4 2"
              />
              <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                {data.histogram_bins.map((bin, i) => (
                  <Cell key={i} fill={barFill(bin.x0, bin.x1)} fillOpacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="flex gap-4 mt-2 flex-wrap">
          {[
            { color: '#34d399', label: 'Normal (|z|<1)' },
            { color: '#f59e0b', label: 'Watch (1≤|z|<threshold)' },
            { color: '#ef4444', label: `Outlier (|z|≥${threshold.toFixed(1)})` },
          ].map(({ color, label }) => (
            <span key={label} className="flex items-center gap-1 text-[9px] text-gray-500">
              <span
                className="inline-block w-2 h-2 rounded-sm flex-shrink-0"
                style={{ background: color }}
              />
              {label}
            </span>
          ))}
        </div>
      </div>

      {/* ── Outlier table ── */}
      {outlierCount > 0 && (
        <div className="bg-secondary border border-white/5 rounded-lg overflow-hidden">
          <p className="text-[10px] text-gray-600 uppercase tracking-wider px-4 py-2 border-b border-white/5">
            Outlier rows — |z| ≥ {threshold.toFixed(1)}
          </p>
          <div className="overflow-auto max-h-64">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="border-b border-white/5">
                  {['Row', 'Value', 'Z-Score', 'Status'].map(h => (
                    <th
                      key={h}
                      className={`px-4 py-1.5 text-gray-600 font-normal ${
                        h === 'Row' ? 'text-left' : h === 'Status' ? 'text-center' : 'text-right'
                      }`}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {outliers.slice(0, 200).map(row => {
                  const s   = statusOf(row.z_score)
                  const { cls, Icon, label } = STATUS_STYLE[s]
                  return (
                    <tr key={row.idx} className="border-b border-white/5 hover:bg-white/[0.02]">
                      <td className="px-4 py-1.5 text-gray-400">{row.idx}</td>
                      <td className="px-4 py-1.5 text-right text-white font-mono">
                        {row.value.toLocaleString('vi-VN', { maximumFractionDigits: 4 })}
                      </td>
                      <td className={`px-4 py-1.5 text-right font-mono font-semibold ${cls}`}>
                        {row.z_score > 0 ? '+' : ''}{row.z_score.toFixed(3)}
                      </td>
                      <td className="px-4 py-1.5 text-center">
                        <span className={`flex items-center justify-center gap-1 ${cls}`}>
                          <Icon size={10} /> {label}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {outliers.length > 200 && (
            <p className="text-[10px] text-gray-600 px-4 py-1.5 border-t border-white/5">
              ... và {outliers.length - 200} dòng nữa — Download CSV để xem tất cả
            </p>
          )}
        </div>
      )}

      {outlierCount === 0 && (
        <p className="text-[11px] text-work text-center py-2">
          ✓ Không có outlier nào với ngưỡng |z| ≥ {threshold.toFixed(1)}
        </p>
      )}

      {/* ── Download ── */}
      <div>
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors disabled:opacity-40"
        >
          <Download size={12} />
          {downloading ? 'Đang tải...' : 'Download Standardized CSV'}
        </button>
        <p className="text-[9px] text-gray-700 mt-0.5">
          CSV gốc + cột z_score + z_status (threshold cố định 2.0)
        </p>
      </div>

    </div>
  )
}
