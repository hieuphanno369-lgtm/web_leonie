import { useState } from 'react'
import { Play } from 'lucide-react'

interface Props {
  disabled: boolean
  running: boolean
  error: string
  onRun: (sql: string) => void
}

const STEPS = [100, 200, 300, 500, 750, 1000]

export default function MlSqlEditor({ disabled, running, error, onRun }: Props) {
  const [limitIdx, setLimitIdx] = useState(0)   // index into STEPS
  const limit = STEPS[limitIdx]

  return (
    <div className="border-t border-white/5 px-3 py-3 space-y-3">
      {/* Row count control */}
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] uppercase tracking-widest text-gray-600">Preview rows</span>
        <span className="text-[11px] font-semibold text-data tabular-nums">{limit.toLocaleString()}</span>
      </div>

      {/* Slider */}
      <div className="space-y-1">
        <input
          type="range"
          min={0}
          max={STEPS.length - 1}
          step={1}
          value={limitIdx}
          onChange={e => setLimitIdx(Number(e.target.value))}
          disabled={disabled}
          className="w-full h-1 accent-data cursor-pointer disabled:opacity-30"
        />
        <div className="flex justify-between text-[9px] text-gray-700">
          <span>100</span>
          <span>1 000</span>
        </div>
      </div>

      {error && (
        <p className="text-danger text-[10px] leading-snug bg-danger/5 rounded px-2 py-1">{error}</p>
      )}

      {/* Run button */}
      <button
        onClick={() => onRun(`SELECT * FROM data LIMIT ${limit}`)}
        disabled={disabled || running}
        className="w-full flex items-center justify-center gap-1.5 text-xs font-medium
                   bg-data/10 hover:bg-data/20 text-data border border-data/20
                   rounded-lg py-2 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
      >
        {running
          ? <><span className="w-3 h-3 border border-data/40 border-t-data rounded-full animate-spin" /> Running…</>
          : <><Play size={11} /> Run Preview</>
        }
      </button>
    </div>
  )
}
