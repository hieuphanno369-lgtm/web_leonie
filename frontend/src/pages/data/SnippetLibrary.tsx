import { useEffect, useState } from 'react'
import { Copy, Edit2, Trash2, Plus, ExternalLink, Search, ChevronDown, ChevronRight, Tag } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import vscDarkPlus from 'react-syntax-highlighter/dist/esm/styles/prism/vsc-dark-plus'
import {
  fetchSnippets, createSnippet, updateSnippet, deleteSnippet,
  type Snippet, type SnippetIn,
} from '../../api/snippets'
import { MSG } from '../../messages'

const CATEGORIES = ['all', 'data', 'ad_hoc', 'metric', 'join', 'filter', 'template', 'other']

const CAT_COLOR: Record<string, string> = {
  data:     'bg-cyan-900 text-cyan-300',
  ad_hoc:   'bg-blue-900 text-blue-300',
  metric:   'bg-purple-900 text-purple-300',
  join:     'bg-green-900 text-green-300',
  filter:   'bg-yellow-900 text-yellow-300',
  template: 'bg-orange-900 text-orange-300',
  other:    'bg-gray-700 text-gray-300',
}

const EMPTY: SnippetIn = { title: '', category: 'ad_hoc', sql: '', tags: '' }

function SnippetModal({
  initial, onSave, onClose,
}: { initial: SnippetIn; onSave: (s: SnippetIn) => void; onClose: () => void }) {
  const [form, setForm] = useState<SnippetIn>(initial)
  const set = (k: keyof SnippetIn) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-2xl p-6 space-y-4" onClick={e => e.stopPropagation()}>
        <h2 className="text-lg font-semibold text-white">{initial.title ? 'Edit Snippet' : 'New Snippet'}</h2>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Title</label>
            <input value={form.title} onChange={set('title')}
              className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
              placeholder="VD: Monthly GMV by brand" />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Category</label>
            <select value={form.category} onChange={set('category')}
              className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
              {CATEGORIES.filter(c => c !== 'all').map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">SQL</label>
          <textarea value={form.sql} onChange={set('sql')} rows={10}
            className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500 resize-y"
            placeholder="SELECT ..." />
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">Tags (comma-separated)</label>
          <input value={form.tags} onChange={set('tags')}
            className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            placeholder="VD: gmv, brand, monthly" />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-300 hover:text-white">Cancel</button>
          <button onClick={() => form.title && form.sql && onSave(form)}
            className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg disabled:opacity-40"
            disabled={!form.title || !form.sql}>
            Save
          </button>
        </div>
      </div>
    </div>
  )
}

function SnippetCard({
  snippet, onEdit, onDelete,
}: { snippet: Snippet; onEdit: () => void; onDelete: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)
  const navigate = useNavigate()

  const copy = () => {
    navigator.clipboard.writeText(snippet.sql)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const openInSandbox = () => {
    localStorage.setItem('sql_sandbox_inject', snippet.sql)
    navigate('/data/sql-sandbox')
  }

  const preview = snippet.sql.slice(0, 120) + (snippet.sql.length > 120 ? '…' : '')
  const tags = snippet.tags ? snippet.tags.split(',').map(t => t.trim()).filter(Boolean) : []

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 space-y-3 hover:border-gray-600 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-white truncate">{snippet.title}</h3>
            <span className={`text-xs px-2 py-0.5 rounded-full ${CAT_COLOR[snippet.category] ?? CAT_COLOR.other}`}>
              {snippet.category}
            </span>
          </div>
          {tags.length > 0 && (
            <div className="flex items-center gap-1 mt-1 flex-wrap">
              <Tag size={10} className="text-gray-500" />
              {tags.map(t => (
                <span key={t} className="text-xs text-gray-500">{t}</span>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button onClick={copy} title="Copy SQL"
            className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors">
            <Copy size={14} />
          </button>
          <button onClick={openInSandbox} title="Open in SQL Sandbox"
            className="p-1.5 text-gray-400 hover:text-blue-400 hover:bg-gray-700 rounded transition-colors">
            <ExternalLink size={14} />
          </button>
          <button onClick={onEdit} title="Edit"
            className="p-1.5 text-gray-400 hover:text-yellow-400 hover:bg-gray-700 rounded transition-colors">
            <Edit2 size={14} />
          </button>
          <button onClick={onDelete} title="Delete"
            className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-gray-700 rounded transition-colors">
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {copied && <p className="text-xs text-green-400">Copied!</p>}

      <div className="relative">
        <div className={`rounded overflow-hidden text-xs ${!expanded ? 'max-h-24 overflow-y-hidden' : ''}`}>
          <SyntaxHighlighter
            language="sql"
            style={vscDarkPlus}
            customStyle={{
              margin: 0,
              padding: '10px 12px',
              background: '#0d1117',
              fontSize: '11px',
              lineHeight: '1.6',
              borderRadius: '6px',
            }}
            wrapLines={false}
            wrapLongLines={false}
          >
            {expanded ? snippet.sql : preview}
          </SyntaxHighlighter>
        </div>
        {snippet.sql.length > 120 && (
          <button onClick={() => setExpanded(e => !e)}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 mt-1">
            {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            {expanded ? 'Collapse' : 'Expand'}
          </button>
        )}
      </div>
    </div>
  )
}

export default function SnippetLibrary() {
  const [snippets, setSnippets] = useState<Snippet[]>([])
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('all')
  const [modal, setModal] = useState<{ open: boolean; snippet?: Snippet }>({ open: false })
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const data = await fetchSnippets(q, category === 'all' ? '' : category)
      setSnippets(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [q, category])

  const handleSave = async (form: SnippetIn) => {
    if (modal.snippet) {
      await updateSnippet(modal.snippet.id, form)
    } else {
      await createSnippet(form)
    }
    setModal({ open: false })
    load()
  }

  const handleDelete = async (id: string) => {
    if (!confirm(MSG.confirmDelete('snippet này'))) return
    await deleteSnippet(id)
    load()
  }

  return (
    <div className="flex h-full bg-gray-950">
      {/* Sidebar */}
      <aside className="w-44 shrink-0 bg-gray-900 border-r border-gray-800 p-4 space-y-1">
        <p className="text-xs text-gray-500 uppercase tracking-widest mb-3">Category</p>
        {CATEGORIES.map(c => (
          <button key={c} onClick={() => setCategory(c)}
            className={`w-full text-left text-sm px-3 py-1.5 rounded-lg transition-colors ${
              category === c ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}>
            {c === 'all' ? 'All' : c}
          </button>
        ))}
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 p-6 space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white">Snippet Library</h1>
            <p className="text-gray-400 text-sm mt-0.5">{snippets.length} snippet{snippets.length !== 1 ? 's' : ''}</p>
          </div>
          <button onClick={() => setModal({ open: true })}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition-colors">
            <Plus size={16} /> New Snippet
          </button>
        </div>

        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input value={q} onChange={e => setQ(e.target.value)}
            placeholder="Tìm theo tiêu đề, SQL, thẻ…"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-9 pr-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>

        {loading ? (
          <p className="text-gray-500 text-sm">{MSG.loading}</p>
        ) : snippets.length === 0 ? (
          <div className="text-center py-20 text-gray-600">
            <p className="text-lg">{MSG.emptySnippets}</p>
            <p className="text-sm mt-1">{MSG.emptySnippetsHint}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 overflow-y-auto overflow-x-hidden pb-4">
            {snippets.map(s => (
              <SnippetCard key={s.id} snippet={s}
                onEdit={() => setModal({ open: true, snippet: s })}
                onDelete={() => handleDelete(s.id)} />
            ))}
          </div>
        )}
      </div>

      {modal.open && (
        <SnippetModal
          initial={modal.snippet ? { title: modal.snippet.title, category: modal.snippet.category, sql: modal.snippet.sql, tags: modal.snippet.tags } : EMPTY}
          onSave={handleSave}
          onClose={() => setModal({ open: false })} />
      )}
    </div>
  )
}
