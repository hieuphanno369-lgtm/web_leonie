import { useEffect, useRef, useState } from 'react'
import type { CorrelationMatrix } from '../../types'

const HEADER_H    = 80   // rotated header row height (px)
const ROW_LABEL_W = 96   // left column for row labels (px)
const LEGEND_H    = 28   // footer for colour legend (px)

interface Props {
  data: CorrelationMatrix
}

/** Diverging scale red ↔ gray ↔ blue. Nonlinear saturation (|r|^0.7) so weak
 *  correlations stay distinguishable from the neutral center. */
function corrToColor(r: number | null): string {
  if (r === null || Number.isNaN(r)) return '#1f2937'   // ô rỗng
  const t = Math.pow(Math.min(Math.abs(r), 1), 0.7)
  const gray = [55, 65, 81]
  const target = r >= 0 ? [37, 99, 235] : [220, 38, 38]  // xanh dương / đỏ
  const mix = gray.map((g, i) => Math.round(g + (target[i] - g) * t))
  return `rgb(${mix[0]}, ${mix[1]}, ${mix[2]})`
}

/** Chọn màu chữ tương phản theo độ sáng nền (sửa bug chữ bị mất ở r thấp). */
function textColor(bg: string): string {
  const m = bg.match(/rgb\((\d+), (\d+), (\d+)\)/)
  if (!m) return '#ffffff'
  const [r, g, b] = [Number(m[1]), Number(m[2]), Number(m[3])]
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return lum > 0.6 ? '#0b0f14' : '#ffffff'
}

/** Truncate to max chars, appending '…' if trimmed. */
function trunc(s: string, max = 12): string {
  return s.length > max ? s.slice(0, max - 1) + '…' : s
}

/** Diễn giải hệ số tương quan Pearson (r) bằng ngôn ngữ tự nhiên. */
function interpret(r: number | null, isSelf: boolean): string {
  if (r === null) return 'Không có dữ liệu'
  if (isSelf) return 'Cùng một cột'
  const abs = Math.abs(r)
  const dir = r >= 0 ? 'thuận' : 'nghịch'
  if (abs >= 0.7) return `Tương quan ${dir} mạnh`
  if (abs >= 0.4) return `Tương quan ${dir} vừa`
  if (abs >= 0.1) return `Tương quan ${dir} yếu`
  return 'Không tương quan'
}

const LEGEND_RS: readonly number[] = [-1, -0.67, -0.33, 0, 0.33, 0.67, 1]
const SWATCH_W = 28  // width of each legend colour swatch (px)

export default function CorrelationHeatmap({ data }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [cell, setCell] = useState(72)
  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => {
      const n = data.columns.length || 1
      const avail = e.contentRect.width - 120     // chừa cột nhãn
      setCell(Math.max(56, Math.min(96, Math.floor(avail / n))))
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [data.columns.length])

  const n         = data.columns.length
  if (n === 0) return <p className="text-[11px] text-gray-500">No numeric columns to correlate.</p>

  const legendW   = LEGEND_RS.length * SWATCH_W
  const svgWidth  = Math.max(ROW_LABEL_W + n * cell, ROW_LABEL_W + legendW)
  const svgHeight = HEADER_H + n * cell + LEGEND_H

  // Centre legend horizontally within the grid area
  const legendX = ROW_LABEL_W + Math.max(0, Math.floor((n * cell - legendW) / 2))
  const legendY = HEADER_H + n * cell   // y-offset where the legend row begins

  return (
    <div className="overflow-auto" ref={wrapRef}>
      <svg
        role="img"
        aria-label={`Correlation heatmap, ${n} variables`}
        width={svgWidth}
        height={svgHeight}
        style={{ fontFamily: 'ui-sans-serif, system-ui, sans-serif', display: 'block' }}
      >
        <title>Correlation heatmap, {n} variables</title>
        {/* ── Column headers — rotated −45° ─────────────────── */}
        {data.columns.map((col, j) => {
          const cx = ROW_LABEL_W + j * cell + cell / 2
          const cy = HEADER_H - 4
          return (
            <text
              key={`ch-${j}`}
              x={cx}
              y={cy}
              fontSize={10}
              fill="#9ca3af"
              textAnchor="start"
              transform={`rotate(-45,${cx},${cy})`}
            >
              {trunc(col)}
            </text>
          )
        })}

        {/* ── Grid cells ────────────────────────────────────── */}
        {data.matrix.map((row, i) =>
          row.map((val, j) => {
            const x       = ROW_LABEL_W + j * cell
            const y       = HEADER_H + i * cell
            const isSelf  = i === j
            const cellBg  = corrToColor(val)
            const txtFill = textColor(cellBg)
            const tipText =
              `${data.columns[i]} × ${data.columns[j]}: ${val !== null ? val.toFixed(2) : '—'}\n${interpret(val, isSelf)}`
            return (
              <g key={`cell-${i}-${j}`}>
                <title>{tipText}</title>
                <rect x={x} y={y} width={cell} height={cell} fill={cellBg} />
                <text
                  x={x + cell / 2}
                  y={y + cell / 2}
                  fontSize={Math.max(10, cell * 0.18)}
                  fill={txtFill}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontWeight="500"
                >
                  {val !== null ? val.toFixed(2) : '—'}
                </text>
              </g>
            )
          })
        )}

        {/* ── Row labels (right-aligned, left margin) ──────── */}
        {data.columns.map((col, i) => (
          <text
            key={`rl-${i}`}
            x={ROW_LABEL_W - 6}
            y={HEADER_H + i * cell + cell / 2}
            fontSize={10}
            fill="#9ca3af"
            textAnchor="end"
            dominantBaseline="middle"
          >
            {trunc(col)}
          </text>
        ))}

        {/* ── Colour legend: 7 swatches r = −1 … +1 ────────── */}
        {LEGEND_RS.map((r, k) => (
          <rect
            key={`sw-${k}`}
            x={legendX + k * SWATCH_W}
            y={legendY + 4}
            width={SWATCH_W}
            height={12}
            fill={corrToColor(r)}
          />
        ))}
        {/* Axis labels below swatches */}
        <text x={legendX}               y={legendY + 24} fontSize={9} fill="#6b7280" textAnchor="middle">{'−1'}</text>
        <text x={legendX + legendW / 2} y={legendY + 24} fontSize={9} fill="#6b7280" textAnchor="middle">0</text>
        <text x={legendX + legendW}     y={legendY + 24} fontSize={9} fill="#6b7280" textAnchor="middle">+1</text>
      </svg>
      {/* Caption below SVG */}
      <p className="text-[9px] text-gray-600 mt-1 text-center select-none">
        Xanh = thuận · Đỏ = nghịch
      </p>
      {data.excluded_columns && data.excluded_columns.length > 0 && (
        <p className="text-[10px] text-gray-500 mt-2">
          Đã loại {data.excluded_columns.length} cột không có biến thiên:{' '}
          {data.excluded_columns
            .map(e => `${e.name} (${e.reason === 'constant' ? 'hằng số' : 'rỗng'})`)
            .join(', ')}
        </p>
      )}
    </div>
  )
}
