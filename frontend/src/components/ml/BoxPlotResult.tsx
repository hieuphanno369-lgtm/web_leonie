import { useState } from 'react'
import { AlertTriangle, Download, BoxSelect, Users } from 'lucide-react'
import type { BoxPlotData, BoxPlotGroup } from '../../types'
import { downloadBoxOutliersCsv, downloadBoxStatsCsv } from '../../api/ml'

interface Props {
  data:              BoxPlotData
  colA:              string
  colB?:             string
  fileId:            string
  maxGroups:         number
  onMaxGroupsChange: (n: number) => void
}

const CAP_OPTIONS = [5, 10, 20, 50]

const SVG_H       = 320
const PAD_TOP     = 20
const PAD_RIGHT   = 20
const PAD_BOTTOM  = 60
const PAD_LEFT    = 50
const SLOT_MIN    = 80

function lerpHex(a: string, b: string, t: number): string {
  const pa = [parseInt(a.slice(1, 3), 16), parseInt(a.slice(3, 5), 16), parseInt(a.slice(5, 7), 16)]
  const pb = [parseInt(b.slice(1, 3), 16), parseInt(b.slice(3, 5), 16), parseInt(b.slice(5, 7), 16)]
  const r = pa.map((c, i) => Math.round(c + (pb[i] - c) * t))
  return `#${r.map(c => c.toString(16).padStart(2, '0')).join('')}`
}

function formatNum(v: number): string {
  return v.toLocaleString('vi-VN', { maximumFractionDigits: 4 })
}

export default function BoxPlotResult({
  data, colA, colB, fileId, maxGroups, onMaxGroupsChange,
}: Props) {
  const [downloadingOutliers, setDownloadingOutliers] = useState(false)
  const [downloadingStats,    setDownloadingStats]    = useState(false)
  const [hoveredIdx,          setHoveredIdx]          = useState<number | null>(null)

  const isGrouped = !!colB
  const groups    = data.groups
  const n         = groups.length

  // ── Color gradient by median (only meaningful in grouped mode) ──
  const medians   = groups.map(g => g.median)
  const minMedian = Math.min(...medians)
  const maxMedian = Math.max(...medians)
  function gradientFill(median: number): string {
    if (!isGrouped || minMedian === maxMedian) return '#fbbf24'
    const t = (median - minMedian) / (maxMedian - minMedian)
    if (t < 0.5) return lerpHex('#34d399', '#fbbf24', t * 2)
    return lerpHex('#fbbf24', '#ef4444', (t - 0.5) * 2)
  }

  // ── SVG dimensions ──
  const W       = Math.max(640, PAD_LEFT + PAD_RIGHT + n * SLOT_MIN)
  const plotW   = W - PAD_LEFT - PAD_RIGHT
  const plotH   = SVG_H - PAD_TOP - PAD_BOTTOM
  const slotW   = plotW / Math.max(1, n)
  const boxW    = Math.min(60, slotW * 0.6)

  // ── Y-scale ──
  const allValues = groups.flatMap(g => [
    g.min, g.max, g.lower_fence, g.upper_fence,
    ...g.outliers.map(o => o.value),
  ])
  const yMinData = Math.min(...allValues)
  const yMaxData = Math.max(...allValues)
  const yPad     = (yMaxData - yMinData) * 0.05 || 1
  const yMin     = yMinData - yPad
  const yMax     = yMaxData + yPad
  const y        = (v: number) => PAD_TOP + (1 - (v - yMin) / (yMax - yMin)) * plotH

  // ── Y-axis ticks (5 evenly-spaced) ──
  const ticks = Array.from({ length: 5 }, (_, i) => yMin + (yMax - yMin) * (i / 4))

  // ── X-axis label rotation ──
  const needRotate = groups.some(g => g.name.length > 8)

  // ── Outlier table data ──
  function signedDistance(value: number, g: BoxPlotGroup): number {
    if (g.iqr === 0) return 0
    if (value > g.upper_fence) return (value - g.q3) / g.iqr
    if (value < g.lower_fence) return (value - g.q1) / g.iqr
    return 0
  }
  const allOutliers = groups.flatMap(g =>
    g.outliers.map(o => ({
      idx:      o.idx,
      value:    o.value,
      group:    g.name,
      distance: signedDistance(o.value, g),
    }))
  ).sort((a, b) => Math.abs(b.distance) - Math.abs(a.distance))

  async function handleDownloadOutliers() {
    setDownloadingOutliers(true)
    try { await downloadBoxOutliersCsv(fileId, colA, colB, maxGroups) }
    finally { setDownloadingOutliers(false) }
  }

  async function handleDownloadStats() {
    setDownloadingStats(true)
    try { await downloadBoxStatsCsv(fileId, colA, colB, maxGroups) }
    finally { setDownloadingStats(false) }
  }

  // ── Hover tooltip (extracted to avoid IIFE issues) ──
  const Tooltip = hoveredIdx !== null ? (() => {
    const g    = groups[hoveredIdx]
    const cx   = PAD_LEFT + slotW * (hoveredIdx + 0.5)
    const tipW = 160
    const tipH = 130
    const tipX = Math.min(W - tipW - 4, Math.max(4, cx + 12))
    const tipY = PAD_TOP + 4
    return (
      <g style={{ pointerEvents: 'none' }}>
        <rect
          x={tipX} y={tipY} width={tipW} height={tipH}
          rx={4} fill="#161b22" stroke="rgba(255,255,255,0.1)"
        />
        {[
          ['name',     g.name],
          ['n',        formatNum(g.n)],
          ['min',      formatNum(g.min)],
          ['Q1',       formatNum(g.q1)],
          ['median',   formatNum(g.median)],
          ['Q3',       formatNum(g.q3)],
          ['max',      formatNum(g.max)],
          ['IQR',      formatNum(g.iqr)],
          ['outliers', String(g.outliers.length)],
        ].map(([k, v], li) => (
          <text
            key={k}
            x={tipX + 8} y={tipY + 14 + li * 13}
            fontSize={10} fill="#d1d5db"
          >
            <tspan fill="#6b7280">{k}:</tspan>{' '}{v}
          </text>
        ))}
      </g>
    )
  })() : null

  return (
    <div className="flex flex-col gap-4">

      {/* ── Summary ── */}
      <div className="bg-secondary border border-white/5 rounded-lg p-4">
        <div className="grid grid-cols-3 gap-3">
          <div>
            <p className="text-[10px] text-gray-600 uppercase tracking-wider">total n</p>
            <p className="text-sm font-semibold text-white">{formatNum(data.total_n)}</p>
          </div>
          <div>
            <p className="text-[10px] text-gray-600 uppercase tracking-wider">
              {isGrouped ? 'groups shown' : 'groups'}
            </p>
            <p className="text-sm font-semibold text-white">
              {n}{isGrouped && data.total_groups !== n ? ` / ${data.total_groups}` : ''}
            </p>
          </div>
          <div>
            <p className="text-[10px] text-gray-600 uppercase tracking-wider">outliers</p>
            <p className={`text-sm font-semibold ${allOutliers.length > 0 ? 'text-danger' : 'text-work'}`}>
              {allOutliers.length}
            </p>
          </div>
        </div>
      </div>

      {/* ── Group cap selector (grouped mode only) ── */}
      {isGrouped && (
        <div className="bg-secondary border border-white/5 rounded-lg p-4 flex items-center gap-3 flex-wrap">
          <span className="text-[10px] text-gray-600 uppercase tracking-wider flex items-center gap-1.5">
            <Users size={11} /> Top groups
          </span>
          <select
            className="input-base text-xs"
            value={maxGroups}
            onChange={e => onMaxGroupsChange(parseInt(e.target.value))}
          >
            {CAP_OPTIONS.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          {data.truncated && (
            <span className="text-[11px] text-gray-500">
              showing top {n} of {data.total_groups} groups (by count)
            </span>
          )}
        </div>
      )}

      {/* ── SVG Box Plot ── */}
      <div className="bg-secondary border border-white/5 rounded-lg p-4">
        <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-2 flex items-center gap-1.5">
          <BoxSelect size={12} /> Box Plot
        </p>
        <div className="overflow-x-auto">
          <svg
            width="100%"
            viewBox={`0 0 ${W} ${SVG_H}`}
            preserveAspectRatio="xMidYMid meet"
            style={{ minWidth: W, height: SVG_H }}
          >
            {/* Y-axis ticks + grid lines */}
            {ticks.map((t, i) => (
              <g key={i}>
                <line
                  x1={PAD_LEFT} x2={W - PAD_RIGHT}
                  y1={y(t)} y2={y(t)}
                  stroke="rgba(255,255,255,0.05)"
                  strokeDasharray="3 3"
                />
                <text
                  x={PAD_LEFT - 6} y={y(t)}
                  textAnchor="end" dominantBaseline="middle"
                  fontSize={9} fill="#6b7280"
                >
                  {formatNum(t)}
                </text>
              </g>
            ))}

            {/* Boxes */}
            {groups.map((g, i) => {
              const cx      = PAD_LEFT + slotW * (i + 0.5)
              const x0      = cx - boxW / 2
              const fill    = gradientFill(g.median)
              const isHover = hoveredIdx === i
              return (
                <g key={g.name}
                  onMouseEnter={() => setHoveredIdx(i)}
                  onMouseLeave={() => setHoveredIdx(null)}
                  style={{ cursor: 'pointer' }}
                >
                  {/* Invisible hit area for tooltip */}
                  <rect
                    x={cx - slotW / 2} y={PAD_TOP}
                    width={slotW} height={plotH}
                    fill="transparent"
                  />

                  {/* Whisker line (upper) */}
                  <line
                    x1={cx} x2={cx}
                    y1={y(g.q3)} y2={y(g.upper_fence)}
                    stroke="rgba(255,255,255,0.4)" strokeWidth={1}
                  />
                  {/* Whisker cap (upper) */}
                  <line
                    x1={cx - 10} x2={cx + 10}
                    y1={y(g.upper_fence)} y2={y(g.upper_fence)}
                    stroke="rgba(255,255,255,0.4)" strokeWidth={1}
                  />
                  {/* Whisker line (lower) */}
                  <line
                    x1={cx} x2={cx}
                    y1={y(g.q1)} y2={y(g.lower_fence)}
                    stroke="rgba(255,255,255,0.4)" strokeWidth={1}
                  />
                  {/* Whisker cap (lower) */}
                  <line
                    x1={cx - 10} x2={cx + 10}
                    y1={y(g.lower_fence)} y2={y(g.lower_fence)}
                    stroke="rgba(255,255,255,0.4)" strokeWidth={1}
                  />

                  {/* Box */}
                  <rect
                    x={x0} y={y(g.q3)}
                    width={boxW} height={y(g.q1) - y(g.q3)}
                    fill={fill} fillOpacity={isHover ? 0.6 : 0.4}
                    stroke={fill} strokeOpacity={0.9} strokeWidth={1}
                    rx={2}
                  />

                  {/* Median line */}
                  <line
                    x1={x0} x2={x0 + boxW}
                    y1={y(g.median)} y2={y(g.median)}
                    stroke="#ffffff" strokeWidth={2}
                  />

                  {/* Outlier dots */}
                  {g.outliers.map((o, oi) => (
                    <circle
                      key={oi}
                      cx={cx} cy={y(o.value)} r={3}
                      fill={fill} stroke="#ffffff" strokeWidth={1}
                    />
                  ))}

                  {/* X-axis label */}
                  <text
                    x={cx} y={SVG_H - PAD_BOTTOM + 14}
                    textAnchor={needRotate ? 'end' : 'middle'}
                    fontSize={10} fill="#9ca3af"
                    transform={needRotate ? `rotate(-35, ${cx}, ${SVG_H - PAD_BOTTOM + 14})` : undefined}
                  >
                    {g.name.length > 14 ? g.name.slice(0, 12) + '…' : g.name}
                  </text>
                </g>
              )
            })}

            {/* Hover tooltip */}
            {Tooltip}
          </svg>
        </div>

        {/* Gradient legend (grouped mode only) */}
        {isGrouped && groups.length > 1 && (
          <div className="flex items-center gap-2 mt-2">
            <span className="text-[9px] text-gray-500">Low median</span>
            <svg width="160" height="10">
              <defs>
                <linearGradient id="medianGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%"   stopColor="#34d399" />
                  <stop offset="50%"  stopColor="#fbbf24" />
                  <stop offset="100%" stopColor="#ef4444" />
                </linearGradient>
              </defs>
              <rect width="160" height="8" y="1" fill="url(#medianGradient)" rx="2" />
            </svg>
            <span className="text-[9px] text-gray-500">High median</span>
          </div>
        )}
      </div>

      {/* ── Outlier table ── */}
      {allOutliers.length > 0 && (
        <div className="bg-secondary border border-white/5 rounded-lg overflow-hidden">
          <p className="text-[10px] text-gray-600 uppercase tracking-wider px-4 py-2 border-b border-white/5">
            Outlier rows — v&#432;&#7907;t 1.5&#215;IQR fence
          </p>
          <div className="overflow-auto max-h-64">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="border-b border-white/5">
                  <th className="px-4 py-1.5 text-gray-600 font-normal text-left">Row</th>
                  {isGrouped && <th className="px-4 py-1.5 text-gray-600 font-normal text-left">Group</th>}
                  <th className="px-4 py-1.5 text-gray-600 font-normal text-right">Value</th>
                  <th className="px-4 py-1.5 text-gray-600 font-normal text-right">Distance</th>
                  <th className="px-4 py-1.5 text-gray-600 font-normal text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {allOutliers.slice(0, 200).map((o, i) => (
                  <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                    <td className="px-4 py-1.5 text-gray-400">{o.idx}</td>
                    {isGrouped && <td className="px-4 py-1.5 text-gray-300">{o.group}</td>}
                    <td className="px-4 py-1.5 text-right text-white font-mono">
                      {formatNum(o.value)}
                    </td>
                    <td className="px-4 py-1.5 text-right font-mono font-semibold text-danger">
                      {o.distance > 0 ? '+' : ''}{o.distance.toFixed(2)}&#215;IQR
                    </td>
                    <td className="px-4 py-1.5 text-center">
                      <span className="flex items-center justify-center gap-1 text-danger">
                        <AlertTriangle size={10} /> Outlier
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {allOutliers.length > 200 && (
            <p className="text-[10px] text-gray-600 px-4 py-1.5 border-t border-white/5">
              ... v&#224; {allOutliers.length - 200} d&#242;ng n&#7919;a — Download CSV &#273;&#7875; xem t&#7845;t c&#7843;
            </p>
          )}
        </div>
      )}

      {allOutliers.length === 0 && (
        <p className="text-[11px] text-work text-center py-2">
          &#10003; Kh&#244;ng c&#243; outlier n&#224;o (to&#224;n b&#7897; gi&#225; tr&#7883; n&#7857;m trong fence 1.5&#215;IQR)
        </p>
      )}

      {/* ── Download buttons ── */}
      <div className="flex gap-6 flex-wrap">
        <button
          onClick={handleDownloadOutliers}
          disabled={downloadingOutliers || allOutliers.length === 0}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors disabled:opacity-40"
        >
          <Download size={12} />
          {downloadingOutliers ? '&#272;ang t&#7843;i...' : 'Download Outliers CSV'}
        </button>
        <button
          onClick={handleDownloadStats}
          disabled={downloadingStats}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors disabled:opacity-40"
        >
          <Download size={12} />
          {downloadingStats ? '&#272;ang t&#7843;i...' : 'Download Box Stats CSV'}
        </button>
      </div>

    </div>
  )
}
