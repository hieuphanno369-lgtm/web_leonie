import { useState } from 'react'
import { ChevronDown, ChevronRight, BookOpen } from 'lucide-react'
import { METRIC_GROUPS, CONTEXT_TABLE } from '../../data/metrics_dictionary'

type TabId = 'metrics' | 'rules' | 'context'

export default function MetricsDictPanel() {
  const [open,           setOpen]           = useState(false)
  const [tab,            setTab]            = useState<TabId>('metrics')
  const [expandedGroup,  setExpandedGroup]  = useState<string | null>(null)
  const [expandedMetric, setExpandedMetric] = useState<string | null>(null)

  function toggleGroup(id: string) {
    setExpandedGroup(g => g === id ? null : id)
    setExpandedMetric(null)
  }

  const TAB_CLS = (t: TabId) =>
    `text-[10px] px-2 py-0.5 rounded transition-colors ${
      tab === t
        ? 'bg-analytics/20 text-analytics'
        : 'text-gray-600 hover:text-gray-400'
    }`

  return (
    <div className="border-t border-white/5 flex-shrink-0">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/3 transition-colors text-left"
      >
        <BookOpen size={11} className="text-analytics flex-shrink-0" />
        <span className="text-[11px] font-semibold text-gray-300 flex-1">Metrics Dict</span>
        {open
          ? <ChevronDown  size={11} className="text-gray-600" />
          : <ChevronRight size={11} className="text-gray-600" />}
      </button>

      {open && (
        <div className="pb-1">
          {/* Tab bar */}
          <div className="flex gap-1 px-3 pb-2">
            {(['metrics','rules','context'] as TabId[]).map(t => (
              <button key={t} className={TAB_CLS(t)} onClick={() => setTab(t)}>
                {t === 'metrics' ? 'Metrics' : t === 'rules' ? 'Rules' : 'Context'}
              </button>
            ))}
          </div>

          {/* Metrics tab */}
          {tab === 'metrics' && (
            <div className="max-h-72 overflow-y-auto">
              {METRIC_GROUPS.map(group => (
                <div key={group.id}>
                  <button
                    onClick={() => toggleGroup(group.id)}
                    className="w-full flex items-center gap-1.5 px-3 py-1.5 hover:bg-white/3 text-left"
                  >
                    {expandedGroup === group.id
                      ? <ChevronDown  size={10} className="text-gray-600 flex-shrink-0" />
                      : <ChevronRight size={10} className="text-gray-600 flex-shrink-0" />}
                    <span className="text-[10px] font-semibold text-gray-400">{group.label}</span>
                    <span className="text-[9px] text-gray-700 ml-auto">{group.metrics.length}</span>
                  </button>

                  {expandedGroup === group.id && (
                    <div className="pl-4">
                      {group.metrics.map(m => (
                        <div key={m.name}>
                          <button
                            onClick={() => setExpandedMetric(n => n === m.name ? null : m.name)}
                            className="w-full flex items-center gap-1 px-3 py-1 hover:bg-white/3 text-left"
                          >
                            <span className="text-[10px] font-mono text-analytics flex-1">{m.name}</span>
                            {expandedMetric === m.name
                              ? <ChevronDown  size={9} className="text-gray-700" />
                              : <ChevronRight size={9} className="text-gray-700" />}
                          </button>

                          {expandedMetric === m.name && (
                            <div className="px-3 pb-2 space-y-1">
                              <p className="text-[10px] text-gray-400 leading-relaxed">{m.definition}</p>
                              <pre className="text-[9px] font-mono text-green-300/80 bg-green-950/20 rounded px-2 py-1 whitespace-pre-wrap leading-relaxed">
                                {m.formula}
                              </pre>
                              {m.notes && (
                                <p className="text-[9px] text-yellow-400/70 leading-relaxed">! {m.notes}</p>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Rules tab */}
          {tab === 'rules' && (
            <div className="max-h-72 overflow-y-auto px-3 space-y-3 pb-2">
              {METRIC_GROUPS.map(group => (
                <div key={group.id}>
                  <p className="text-[9px] text-gray-600 uppercase tracking-wider mb-1">{group.label}</p>
                  {group.metrics.map(m => (
                    <div key={m.name} className="mb-1.5">
                      <span className="text-[9px] font-mono text-analytics">-- {m.name}</span>
                      <pre className="text-[9px] font-mono text-gray-400 bg-white/3 rounded px-2 py-1 whitespace-pre-wrap leading-relaxed mt-0.5">
                        {m.formula}
                      </pre>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}

          {/* Context tab: FMCG Corp vs VINA BREW */}
          {tab === 'context' && (
            <div className="max-h-72 overflow-y-auto px-2 pb-2">
              <p className="text-[9px] text-gray-600 px-1 pb-1.5">So sanh terminology FMCG Corp - VINA BREW</p>
              <table className="w-full text-[9px] border-collapse">
                <thead>
                  <tr>
                    {['Khai niem', 'FMCG Corp', 'VINA BREW'].map(h => (
                      <th key={h} className="text-left text-gray-600 uppercase tracking-wider px-1 py-1 border-b border-white/5">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {CONTEXT_TABLE.map((row, i) => (
                    <tr key={i} className="hover:bg-white/3 border-b border-white/3">
                      <td className="px-1 py-1 text-gray-500 font-medium">{row.concept}</td>
                      <td className="px-1 py-1 text-gray-500">{row.fmcgcorp}</td>
                      <td className="px-1 py-1 text-analytics">{row.vinabrew}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
