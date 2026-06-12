import { useState } from 'react'
import { AlertTriangle, CheckCircle, ChevronDown, ChevronUp } from 'lucide-react'
import type { QualityResult } from '../../types'
import { MSG } from '../../messages'

interface Props {
  quality: QualityResult | null
  qualityError?: boolean
}

const BADGE_STYLE: Record<string, string> = {
  null:      'bg-[#f87171]/10 text-[#f87171] border border-[#f87171]/20',
  outlier:   'bg-[#fb923c]/10 text-[#fb923c] border border-[#fb923c]/20',
  duplicate: 'bg-[#fbbf24]/10 text-[#fbbf24] border border-[#fbbf24]/20',
  constant:  'bg-[#9ca3af]/10 text-[#9ca3af] border border-[#9ca3af]/20',
  dtype:     'bg-[#a78bfa]/10 text-[#a78bfa] border border-[#a78bfa]/20',
}

const BADGE_LABEL: Record<string, string> = {
  null: 'NULL', outlier: 'OUTLIER', duplicate: 'DUPLIC.', constant: 'CONSTANT', dtype: 'DTYPE',
}

export default function DataQualityBanner({ quality, qualityError }: Props) {
  const [expanded, setExpanded] = useState(false)

  if (qualityError) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 bg-red-500/5 border-b border-red-500/10 text-red-400 text-xs flex-shrink-0">
        <AlertTriangle size={13} />
        {MSG.qualityCheckFailed}
      </div>
    )
  }

  if (!quality) return null

  if (quality.issue_count === 0) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 bg-emerald-500/5 border-b border-emerald-500/10 text-emerald-400 text-xs flex-shrink-0">
        <CheckCircle size={13} />
        {MSG.qualityNoIssues}
      </div>
    )
  }

  return (
    <div className="border-b border-yellow-500/20 bg-yellow-500/5 flex-shrink-0">
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center justify-between px-4 py-2 text-xs text-yellow-400 hover:bg-yellow-500/5 transition-colors"
      >
        <span className="flex items-center gap-2">
          <AlertTriangle size={13} />
          {MSG.qualityIssuesFound(quality.issue_count)}
        </span>
        {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
      </button>

      {expanded && (
        <div className="px-4 pb-3 flex flex-col gap-1.5">
          {quality.issues.map((issue, i) => (
            <div key={i} className="flex items-center gap-3 text-xs">
              <span className="text-gray-400 font-mono w-32 truncate flex-shrink-0">
                {issue.column ?? '—'}
              </span>
              <span className="text-gray-300 flex-1">{issue.detail}</span>
              <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded flex-shrink-0 ${BADGE_STYLE[issue.type] ?? ''}`}>
                {BADGE_LABEL[issue.type] ?? issue.type.toUpperCase()}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
