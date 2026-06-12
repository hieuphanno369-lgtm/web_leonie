import { useState } from 'react'
import { X, ChevronDown, ChevronRight } from 'lucide-react'
import { VINA_BREW_EXERCISES } from '../../data/vina_brew_exercises'
import { SCHEMA_META } from '../../data/vina_brew_schema_meta'

const DIFF_CLS: Record<string, string> = {
  easy:   'bg-green-900/60 text-green-400',
  medium: 'bg-yellow-900/60 text-yellow-400',
  hard:   'bg-red-900/60 text-red-400',
}

const TSQL_DICT_LABEL = (
  <span className="text-[9px] text-yellow-400/70 font-normal ml-1">[T-SQL alt]</span>
)

interface Props {
  selectedExId: string | null
  onClose: () => void
}

export default function QuerySuggestPanel({ selectedExId, onClose }: Props) {
  const ex = selectedExId
    ? VINA_BREW_EXERCISES.find(e => e.id === selectedExId) ?? null
    : null

  // Infer schema hints: tables referenced in the solution
  const schemaTables = ex
    ? Object.keys(SCHEMA_META).filter(t =>
        ex.solutionQuery.toLowerCase().includes(t.toLowerCase())
      )
    : []

  return (
    <div className="w-[260px] border-l border-white/5 flex flex-col flex-shrink-0 overflow-hidden bg-[#0d1117]">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-white/5 flex-shrink-0">
        <span className="text-[11px] font-semibold text-gray-300 flex-1">Query Suggest</span>
        <button onClick={onClose} className="text-gray-600 hover:text-gray-400">
          <X size={12} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
        {!ex ? (
          <div className="p-3 text-center">
            <p className="text-[10px] text-gray-600 leading-relaxed">
              Chọn một bài tập từ panel bên trái để xem gợi ý.
            </p>
          </div>
        ) : (
          <div className="p-3 space-y-3">
            {/* Exercise info */}
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className={`text-[9px] px-1.5 rounded ${DIFF_CLS[ex.difficulty]}`}>
                  {ex.difficulty}
                </span>
                <span className="text-[9px] text-gray-600">{ex.category}</span>
              </div>
              <p className="text-[11px] font-semibold text-white">{ex.title}</p>
              <p className="text-[10px] text-blue-300/60 leading-relaxed">{ex.businessContext}</p>
            </div>

            <hr className="border-white/5" />

            {/* Hint tier 1 — Direction */}
            <Section title="Hướng tiếp cận" defaultOpen>
              <p className="text-[10px] text-gray-400 leading-relaxed whitespace-pre-wrap">
                {ex.hints[0]}
              </p>
            </Section>

            {/* Hint tier 2 — Keywords + T-SQL */}
            <Section title={<>Keywords {TSQL_DICT_LABEL}</>}>
              <pre className="text-[9px] font-mono text-yellow-300/80 bg-yellow-950/20 rounded px-2 py-1.5 whitespace-pre-wrap leading-relaxed">
                {ex.hints[1]}
              </pre>
            </Section>

            {/* Hint tier 3 — Full solution */}
            <Section title="Xem đáp án">
              <pre className="text-[9px] font-mono text-green-300/80 bg-green-950/20 rounded px-2 py-1.5 whitespace-pre-wrap leading-relaxed">
                {ex.hints[2]}
              </pre>
            </Section>

            {/* Schema hint */}
            {schemaTables.length > 0 && (
              <Section title="Schema tables dùng">
                <div className="space-y-2">
                  {schemaTables.map(tableName => {
                    const meta = SCHEMA_META[tableName]
                    if (!meta) return null
                    // Only show columns that appear in the solution query
                    const usedCols = Object.keys(meta).filter(col =>
                      ex.solutionQuery.toLowerCase().includes(col.toLowerCase())
                    )
                    if (!usedCols.length) return null
                    return (
                      <div key={tableName}>
                        <p className="text-[9px] font-mono text-data mb-0.5">{tableName}</p>
                        {usedCols.map(col => (
                          <div key={col} className="flex gap-1.5 px-1 py-0.5">
                            <span className="text-[9px] font-mono text-gray-400 flex-shrink-0">{col}</span>
                            <span className="text-[9px] text-gray-600 leading-relaxed">{meta[col]}</span>
                          </div>
                        ))}
                      </div>
                    )
                  })}
                </div>
              </Section>
            )}

            {/* Expected columns */}
            <div className="bg-white/3 rounded px-2 py-1.5">
              <p className="text-[9px] text-gray-600 mb-0.5">Expected columns:</p>
              <p className="text-[10px] font-mono text-analytics">
                {ex.expectedColumns.join(', ')}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Collapsible section ───────────────────────────────────────────────────────
function Section({
  title,
  children,
  defaultOpen = false,
}: {
  title: React.ReactNode
  children: React.ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div>
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1 w-full text-left mb-1"
      >
        {open
          ? <ChevronDown  size={10} className="text-gray-600 flex-shrink-0" />
          : <ChevronRight size={10} className="text-gray-600 flex-shrink-0" />}
        <span className="text-[10px] font-semibold text-gray-500">{title}</span>
      </button>
      {open && children}
    </div>
  )
}

