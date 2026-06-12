import { Check, Split, Sparkles } from 'lucide-react'
import type { FieldGroupSuggestion } from '../../../types'

interface Props {
  suggestions: FieldGroupSuggestion[]
  accepted: Record<string, string[]>   // canonical -> members (accepted groups)
  onAccept: (s: FieldGroupSuggestion) => void
  onSplit: (canonical: string) => void
}

const REASON_LABEL: Record<string, string> = {
  type: 'gộp theo loại giá trị',
  name: 'gộp theo tên cột',
  'name+type': 'tên + loại giống nhau',
}

export default function MergeUnifySuggestions({ suggestions, accepted, onAccept, onSplit }: Props) {
  if (suggestions.length === 0) {
    return <p className="text-[11px] text-gray-600">Không có gợi ý gộp cột.</p>
  }
  return (
    <div className="space-y-2">
      <p className="text-[11px] uppercase tracking-wide text-gray-600 flex items-center gap-1">
        <Sparkles size={12} /> Gợi ý gộp cột
      </p>
      {suggestions.map(s => {
        const isAccepted = !!accepted[s.canonical]
        return (
          <div key={s.canonical}
            className="rounded-lg border border-white/10 bg-white/5 p-2.5 space-y-1.5">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-medium text-gray-100">{s.canonical}</span>
              <span className="badge bg-analytics/15 text-analytics">{s.inferred_type}</span>
            </div>
            <p className="text-[11px] text-gray-400">
              {s.members.join(' · ')} — {REASON_LABEL[s.reason] ?? s.reason}
              <span className="text-gray-600"> ({Math.round(s.confidence * 100)}%)</span>
            </p>
            <div className="flex gap-1.5">
              {isAccepted ? (
                <button onClick={() => onSplit(s.canonical)}
                  className="flex items-center gap-1 rounded bg-white/5 px-2 py-1 text-[11px] text-gray-300 hover:bg-white/10">
                  <Split size={11} /> Tách lại
                </button>
              ) : (
                <button onClick={() => onAccept(s)}
                  className="flex items-center gap-1 rounded bg-data/20 px-2 py-1 text-[11px] text-data hover:bg-data/30">
                  <Check size={11} /> Đồng ý gộp
                </button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
