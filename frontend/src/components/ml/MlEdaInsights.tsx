import { useState } from 'react'
import { Lightbulb, Target, Hash, Copy, Check } from 'lucide-react'
import type { EdaReport } from '../../types'
import { edaToMarkdown } from './edaMarkdown'

const SEV: Record<string, string> = {
  high: 'border-red-500/40', medium: 'border-amber-500/40', low: 'border-data/20',
}

export default function MlEdaInsights({ report }: { report: EdaReport }) {
  const [copied, setCopied] = useState(false)
  async function copy() {
    await navigator.clipboard.writeText(edaToMarkdown(report))
    setCopied(true); setTimeout(() => setCopied(false), 1500)
  }
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-400">
          Nguồn insight: {report.insights_source === 'ai' ? 'AI' : 'Quy tắc (rule-based)'}
        </p>
        <button onClick={copy}
          className="flex items-center gap-1 rounded-md border border-data/30 px-2 py-1 text-xs text-gray-200 hover:bg-data/10">
          {copied ? <Check size={13} /> : <Copy size={13} />} Copy Markdown
        </button>
      </div>
      {report.insights.map((i, n) => (
        <div key={n} className={`rounded-lg border p-3 space-y-1.5 ${SEV[i.severity] ?? SEV.low}`}>
          <p className="flex items-center gap-1.5 text-xs font-medium text-data">
            <Hash size={13} /> {i.finding}
          </p>
          <p className="flex items-start gap-1.5 text-xs text-gray-300">
            <Lightbulb size={13} className="mt-0.5 shrink-0" /> {i.so_what}
          </p>
          <p className="flex items-start gap-1.5 text-xs text-gray-300">
            <Target size={13} className="mt-0.5 shrink-0" /> {i.action}
          </p>
        </div>
      ))}
    </div>
  )
}
