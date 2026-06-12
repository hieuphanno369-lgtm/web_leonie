import { useMemo } from 'react'
import type { CorrelationMatrix } from '../../types'

interface Props {
  data: CorrelationMatrix
  topN?: number
}

interface Pair { a: string; b: string; r: number }

/** Same diverging scale as CorrelationHeatmap (blue +, red −). */
function corrToColor(r: number): string {
  const t = Math.pow(Math.min(Math.abs(r), 1), 0.7)
  const gray = [55, 65, 81]
  const target = r >= 0 ? [37, 99, 235] : [220, 38, 38]
  const mix = gray.map((g, i) => Math.round(g + (target[i] - g) * t))
  return `rgb(${mix[0]}, ${mix[1]}, ${mix[2]})`
}

function Row({ p }: { p: Pair }) {
  return (
    <div className="flex items-center gap-2 text-[11px] py-0.5">
      <span className="text-gray-300 truncate flex-1" title={`${p.a} × ${p.b}`}>
        {p.a} <span className="text-gray-600">×</span> {p.b}
      </span>
      <div className="w-20 h-2 rounded bg-white/5 overflow-hidden">
        <div className="h-full" style={{ width: `${Math.min(Math.abs(p.r), 1) * 100}%`, background: corrToColor(p.r) }} />
      </div>
      <span className="tabular-nums w-12 text-right" style={{ color: corrToColor(p.r) }}>
        {p.r >= 0 ? '+' : ''}{p.r.toFixed(2)}
      </span>
    </div>
  )
}

export default function CorrelationRanked({ data, topN = 8 }: Props) {
  const { pos, neg } = useMemo(() => {
    const pairs: Pair[] = []
    for (let i = 0; i < data.columns.length; i++) {
      for (let j = i + 1; j < data.columns.length; j++) {
        const r = data.matrix[i]?.[j]
        if (r === null || r === undefined || Number.isNaN(r)) continue
        pairs.push({ a: data.columns[i], b: data.columns[j], r })
      }
    }
    return {
      pos: pairs.filter(p => p.r > 0).sort((x, y) => y.r - x.r).slice(0, topN),
      neg: pairs.filter(p => p.r < 0).sort((x, y) => x.r - y.r).slice(0, topN),
    }
  }, [data, topN])

  if (pos.length === 0 && neg.length === 0) {
    return <p className="text-[11px] text-gray-600 mt-3">Không có cặp tương quan để xếp hạng.</p>
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-3">
      <div>
        <p className="text-[10px] font-semibold text-blue-400 mb-1">Tương quan DƯƠNG (cùng chiều)</p>
        {pos.length ? pos.map((p, i) => <Row key={i} p={p} />)
                    : <p className="text-[10px] text-gray-600">—</p>}
      </div>
      <div>
        <p className="text-[10px] font-semibold text-red-400 mb-1">Tương quan ÂM (ngược chiều)</p>
        {neg.length ? neg.map((p, i) => <Row key={i} p={p} />)
                    : <p className="text-[10px] text-gray-600">—</p>}
      </div>
    </div>
  )
}
