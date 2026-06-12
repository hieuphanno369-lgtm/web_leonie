import { useState } from 'react'
import { Code2, Copy, Check, Download, ChevronDown, ChevronUp } from 'lucide-react'

interface Props {
  code: string
  filename?: string             // e.g. "stats_analysis.py"
  language?: 'python' | 'sql'   // default 'python'
  defaultOpen?: boolean
}

export default function CodePanel({ code, filename, language = 'python', defaultOpen = false }: Props) {
  const [open,   setOpen]   = useState(defaultOpen)
  const [copied, setCopied] = useState(false)

  const ext    = language === 'sql' ? 'sql' : 'py'
  const mime   = language === 'sql' ? 'text/sql' : 'text/x-python'
  const label  = language === 'sql' ? 'SQL Code' : 'Python Code'
  const dlName = filename ?? `analysis.${ext}`

  function handleCopy() {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  function handleDownload() {
    const blob = new Blob([code], { type: mime })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url; a.download = dlName; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="border border-white/10 rounded-lg overflow-hidden">
      {/* Header toggle */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-[#161b22] hover:bg-white/5 transition-colors text-left"
      >
        <Code2 size={12} className="text-analytics flex-shrink-0" />
        <span className="text-[11px] font-semibold text-gray-300 flex-1">{label}</span>
        <span className="text-[9px] text-gray-600 mr-1">{code.split('\n').length} lines</span>
        {open
          ? <ChevronUp   size={11} className="text-gray-600" />
          : <ChevronDown size={11} className="text-gray-600" />}
      </button>

      {open && (
        <div className="bg-[#0d1117]">
          {/* Toolbar */}
          <div className="flex items-center justify-end gap-3 px-3 py-1.5 border-b border-white/5">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-300 transition-colors"
            >
              {copied ? <Check size={10} className="text-green-400" /> : <Copy size={10} />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <button
              onClick={handleDownload}
              className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-300 transition-colors"
            >
              <Download size={10} /> Download .{ext}
            </button>
          </div>

          {/* Code block */}
          <pre className="text-[11px] font-mono text-gray-300 leading-relaxed p-4 overflow-x-auto whitespace-pre">
            {highlight(code, language)}
          </pre>
        </div>
      )}
    </div>
  )
}

// Minimal keyword highlight — returns React nodes
function highlight(code: string, language: 'python' | 'sql' = 'python') {
  const PY_KEYWORDS  = /\b(import|from|as|def|class|return|for|in|if|else|elif|not|and|or|True|False|None|with|pass|raise|try|except|finally|lambda|yield|async|await|print)\b/g
  const PY_BUILTINS  = /\b(len|range|list|dict|str|int|float|bool|type|isinstance|enumerate|zip|map|filter|sorted|sum|min|max|abs|round|open|np|pl|pd|stats)\b/g
  const PY_COMMENTS  = /(#.*$)/gm
  const SQL_KEYWORDS = /\b(SELECT|FROM|WHERE|GROUP|BY|ORDER|HAVING|LIMIT|OFFSET|JOIN|LEFT|RIGHT|INNER|OUTER|FULL|CROSS|ON|USING|AS|AND|OR|NOT|IN|IS|NULL|LIKE|ILIKE|BETWEEN|CASE|WHEN|THEN|ELSE|END|UNION|ALL|DISTINCT|WITH|INSERT|INTO|VALUES|UPDATE|SET|DELETE|CREATE|TABLE|VIEW|DROP|ALTER|ASC|DESC|OVER|PARTITION|QUALIFY)\b/gi
  const SQL_BUILTINS = /\b(COUNT|SUM|AVG|MIN|MAX|ROUND|CAST|COALESCE|ROW_NUMBER|RANK|DENSE_RANK|LAG|LEAD|DATE_TRUNC|EXTRACT|NOW|CURRENT_DATE|CURRENT_TIMESTAMP|LOWER|UPPER|TRIM|SUBSTRING|LENGTH|ABS|CONCAT)\b/gi
  const SQL_COMMENTS = /(--.*$)/gm

  const KEYWORDS = language === 'sql' ? SQL_KEYWORDS : PY_KEYWORDS
  const BUILTINS = language === 'sql' ? SQL_BUILTINS : PY_BUILTINS
  const COMMENTS = language === 'sql' ? SQL_COMMENTS : PY_COMMENTS
  const STRINGS  = /("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')/g
  const NUMBERS  = /\b(\d+\.?\d*)\b/g

  const lines = code.split('\n')
  return lines.map((line, i) => {
    const parts: React.ReactNode[] = []
    let last = 0
    const tokens: { start: number; end: number; type: string }[] = []

    const addTokens = (re: RegExp, type: string) => {
      let m: RegExpExecArray | null
      const r = new RegExp(re.source, re.flags.replace('g','') + 'g')
      while ((m = r.exec(line)) !== null) {
        tokens.push({ start: m.index, end: m.index + m[0].length, type })
      }
    }

    addTokens(COMMENTS, 'comment')
    addTokens(STRINGS,  'string')
    addTokens(KEYWORDS, 'keyword')
    addTokens(BUILTINS, 'builtin')
    addTokens(NUMBERS,  'number')

    tokens.sort((a, b) => a.start - b.start)

    const used: boolean[] = new Array(line.length).fill(false)
    const clean: typeof tokens = []
    for (const t of tokens) {
      if (!used.slice(t.start, t.end).some(Boolean)) {
        clean.push(t)
        for (let j = t.start; j < t.end; j++) used[j] = true
      }
    }
    clean.sort((a, b) => a.start - b.start)

    for (const t of clean) {
      if (last < t.start) parts.push(line.slice(last, t.start))
      const text = line.slice(t.start, t.end)
      const cls =
        t.type === 'keyword' ? 'text-purple-400' :
        t.type === 'builtin' ? 'text-blue-400'   :
        t.type === 'string'  ? 'text-amber-300'  :
        t.type === 'comment' ? 'text-gray-600 italic' :
        t.type === 'number'  ? 'text-green-400'  : ''
      parts.push(<span key={t.start} className={cls}>{text}</span>)
      last = t.end
    }
    if (last < line.length) parts.push(line.slice(last))

    return <span key={i}>{parts}{'\n'}</span>
  })
}
