import { useState } from 'react'
import CodePanel from '../ml/CodePanel'

interface Props {
  python: string
  sql: string
  jobName: string
}

export default function CodeViewer({ python, sql, jobName }: Props) {
  const [tab, setTab] = useState<'python' | 'sql'>('python')
  const safe = jobName.trim().replace(/[^a-zA-Z0-9_-]+/g, '_') || 'job'

  return (
    <div className="glass-card p-3">
      <div className="flex gap-1 mb-2">
        {(['python', 'sql'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              tab === t ? 'bg-accent/15 text-accent' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {t === 'python' ? 'Python' : 'SQL'}
          </button>
        ))}
      </div>

      {tab === 'python'
        ? <CodePanel code={python} language="python" filename={`${safe}.py`} defaultOpen />
        : <CodePanel code={sql || '-- (passthrough: no shaping SQL)'} language="sql" filename={`${safe}.sql`} defaultOpen />}
    </div>
  )
}
