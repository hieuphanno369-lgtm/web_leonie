import { useMemo } from 'react'
import { X } from 'lucide-react'
import type { MergeStageResult } from '../../../types'
import MlMergeDropzone from '../MlMergeDropzone'
import { parseEventName } from './eventName'

interface Props {
  stage: MergeStageResult | null
  busy: boolean
  onFiles: (files: File[]) => void
  onRemove: (filename: string) => void
  onNext: () => void
}

/** Most common column count; ties resolve to the higher count (treat the fuller schema as "normal"). */
function modeColumns(counts: number[]): number {
  const freq = new Map<number, number>()
  for (const c of counts) freq.set(c, (freq.get(c) ?? 0) + 1)
  let best = 0
  let bestFreq = -1
  for (const [c, f] of freq) {
    if (f > bestFreq || (f === bestFreq && c > best)) { best = c; bestFreq = f }
  }
  return best
}

export default function MergeStepUpload({ stage, busy, onFiles, onRemove, onNext }: Props) {
  const files = stage?.files ?? []
  const mode = useMemo(() => modeColumns(files.map(f => f.fields.length)), [files])

  return (
    <div className="space-y-4">
      <p className="text-xs text-gray-500">
        Tải lên nhiều file (CSV/XLSX) lệch schema. Công cụ sẽ đọc giá trị, đoán loại
        từng cột và gợi ý gộp các cột cùng loại nhưng khác tên.
      </p>

      <MlMergeDropzone onFiles={onFiles} busy={busy} />

      {files.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[11px] uppercase tracking-wide text-gray-600">
            {files.length} file đã tải
          </p>
          {files.map(f => {
            const { event, date, ctx } = parseEventName(f.filename)
            const n = f.fields.length
            const low = n < mode
            const high = n > mode
            const numCls = low
              ? 'font-semibold text-amber-400 [text-shadow:0_0_8px_rgba(251,191,36,0.45)]'
              : high
                ? 'font-semibold text-cyan-300 [text-shadow:0_0_8px_rgba(34,211,238,0.4)]'
                : 'font-semibold text-gray-300'
            const numTitle = low
              ? `Ít cột hơn đa số file (chuẩn ${mode} cột) — có thể thiếu trường`
              : high
                ? `Nhiều cột hơn đa số file (chuẩn ${mode} cột)`
                : undefined
            return (
              <div key={f.filename}
                className="group relative flex items-center gap-3 overflow-hidden rounded-lg border border-white/[0.07] bg-[#10151c] py-2.5 pl-3.5 pr-2.5 transition-[box-shadow,border-color] hover:border-cyan-400/40 hover:shadow-[0_0_18px_-6px_rgba(34,211,238,0.4)]">
                <span aria-hidden
                  className="pointer-events-none absolute inset-y-0 left-0 w-[3px] bg-gradient-to-b from-cyan-400 via-blue-400 to-violet-400 opacity-60 transition-opacity group-hover:opacity-100" />
                <div className="min-w-0 flex-1 truncate" title={f.filename}>
                  <span className="font-semibold text-[#f5fbff]">{event}</span>
                  {date && (
                    <span className="ml-2 rounded bg-violet-400/[0.14] px-1.5 py-0.5 align-middle font-mono text-[10.5px] text-violet-300">
                      {date}
                    </span>
                  )}
                  {ctx && <span className="text-gray-500">{' · ' + ctx}</span>}
                </div>
                <span className="w-[58px] flex-shrink-0 text-right font-mono text-[11.5px] tabular-nums" title={numTitle}>
                  <span className={numCls}>{n}</span>
                  <span className="text-gray-500"> cột</span>
                </span>
                <button onClick={() => onRemove(f.filename)} title="Bỏ file"
                  className="inline-flex h-[22px] w-[22px] flex-shrink-0 items-center justify-center rounded-md text-gray-500 transition-colors hover:bg-danger/10 hover:text-danger">
                  <X size={13} />
                </button>
              </div>
            )
          })}
        </div>
      )}

      <div className="flex justify-end">
        <button onClick={onNext} disabled={busy || files.length === 0}
          className="rounded-md bg-data px-4 py-2 text-xs font-medium text-black disabled:opacity-40">
          Tiếp tục →
        </button>
      </div>
    </div>
  )
}
