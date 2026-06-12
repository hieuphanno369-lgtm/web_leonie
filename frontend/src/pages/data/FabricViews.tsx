import { useEffect, useState } from 'react'
import { Search, Plus, Edit2, Trash2, ChevronDown, ChevronRight, Copy, ExternalLink, Tag } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import vscDarkPlus from 'react-syntax-highlighter/dist/esm/styles/prism/vsc-dark-plus'
import {
  fetchViews, createView, updateView, deleteView,
  type FabricView, type FabricViewIn,
} from '../../api/fabricViews'
import { MSG } from '../../messages'

const CATEGORIES = ['all', 'fact', 'dim', 'report', 'staging']

const CAT_COLOR: Record<string, string> = {
  fact:    'bg-blue-900 text-blue-300',
  dim:     'bg-purple-900 text-purple-300',
  report:  'bg-green-900 text-green-300',
  staging: 'bg-yellow-900 text-yellow-300',
}

const EMPTY: FabricViewIn = { name: '', schema_name: 'dbo', category: 'fact', description: '', sql_def: '', tags: '' }

function ViewModal({
  initial, onSave, onClose,
}: { initial: FabricViewIn; onSave: (v: FabricViewIn) => void; onClose: () => void }) {
  const [form, setForm] = useState<FabricViewIn>(initial)
  const set = (k: keyof FabricViewIn) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-2xl p-6 space-y-4" onClick={e => e.stopPropagation()}>
        <h2 className="text-lg font-semibold text-white">{initial.name ? 'Edit View' : 'New Fabric View'}</h2>

        <div className="grid grid-cols-3 gap-4">
          <div className="col-span-2">
            <label className="block text-xs text-gray-400 mb-1">View Name</label>
            <input value={form.name} onChange={set('name')}
              className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500"
              placeholder="VD: vw_fact_txn_enriched" />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Schema</label>
            <input value={form.schema_name} onChange={set('schema_name')}
              className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500"
              placeholder="dbo" />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Category</label>
            <select value={form.category} onChange={set('category')}
              className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
              {CATEGORIES.filter(c => c !== 'all').map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Tags (comma-separated)</label>
            <input value={form.tags} onChange={set('tags')}
              className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
              placeholder="YTD2026,Cohort,Retention" />
          </div>
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">Description</label>
          <input value={form.description} onChange={set('description')}
            className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            placeholder="Mô tả nội dung của view này" />
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">SQL Definition (T-SQL)</label>
          <textarea value={form.sql_def} onChange={set('sql_def')} rows={10}
            className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500 resize-y"
            placeholder="CREATE OR ALTER VIEW dbo.vw_... AS ..." />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-300 hover:text-white">Cancel</button>
          <button onClick={() => form.name && onSave(form)}
            className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg disabled:opacity-40"
            disabled={!form.name}>
            Save
          </button>
        </div>
      </div>
    </div>
  )
}

function ViewCard({
  view, onEdit, onDelete,
}: { view: FabricView; onEdit: () => void; onDelete: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied]     = useState(false)
  const navigate = useNavigate()

  const copy = () => {
    navigator.clipboard.writeText(view.sql_def)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const openInSandbox = () => {
    localStorage.setItem('sql_sandbox_inject', view.sql_def)
    navigate('/data/sql-sandbox')
  }

  const preview = view.sql_def.slice(0, 200) + (view.sql_def.length > 200 ? '…' : '')
  const tags = view.tags ? view.tags.split(',').map(t => t.trim()).filter(Boolean) : []

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 space-y-3 hover:border-gray-600 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-gray-500 font-mono shrink-0">{view.schema_name}.</span>
            <h3 className="text-sm font-semibold text-white font-mono truncate">{view.name}</h3>
            <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${CAT_COLOR[view.category] ?? 'bg-gray-700 text-gray-300'}`}>
              {view.category}
            </span>
          </div>

          {view.description && (
            <p className="text-xs text-gray-400 mt-1 leading-relaxed">{view.description}</p>
          )}

          {tags.length > 0 && (
            <div className="flex items-center gap-1 mt-1.5 flex-wrap">
              <Tag size={10} className="text-gray-500 shrink-0" />
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

      {/* SQL block */}
      {view.sql_def && (
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
              {expanded ? view.sql_def : preview}
            </SyntaxHighlighter>
          </div>
          {view.sql_def.length > 200 && (
            <button onClick={() => setExpanded(e => !e)}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 mt-1">
              {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              {expanded ? 'Collapse SQL' : 'Expand SQL'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export default function FabricViews() {
  const [views,    setViews]    = useState<FabricView[]>([])
  const [q,        setQ]        = useState('')
  const [category, setCategory] = useState('all')
  const [modal,    setModal]    = useState<{ open: boolean; view?: FabricView }>({ open: false })
  const [loading,  setLoading]  = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      setViews(await fetchViews(q, category === 'all' ? '' : category))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [q, category])

  const handleSave = async (form: FabricViewIn) => {
    if (modal.view) await updateView(modal.view.id, form)
    else            await createView(form)
    setModal({ open: false })
    load()
  }

  const handleDelete = async (id: string) => {
    if (!confirm(MSG.confirmDelete('định nghĩa view này'))) return
    await deleteView(id)
    load()
  }

  return (
    <div className="flex h-full bg-gray-950">
      {/* Sidebar */}
      <aside className="w-44 shrink-0 bg-gray-900 border-r border-gray-800 p-4 space-y-1">
        <p className="text-xs text-gray-500 uppercase tracking-widest mb-3">Category</p>
        {CATEGORIES.map(c => {
          const count = c === 'all' ? views.length : views.filter(v => v.category === c).length
          return (
            <button key={c} onClick={() => setCategory(c)}
              className={`w-full flex items-center justify-between text-sm px-3 py-1.5 rounded-lg transition-colors ${
                category === c ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}>
              <span>{c === 'all' ? 'All' : c}</span>
              <span className="text-xs opacity-60">{count}</span>
            </button>
          )
        })}
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 p-6 space-y-4 overflow-hidden">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white">Fabric Views</h1>
            <p className="text-gray-400 text-sm mt-0.5">
              {views.length} view{views.length !== 1 ? 's' : ''} · Microsoft Fabric SQL Analytics Endpoint
            </p>
          </div>
          <button onClick={() => setModal({ open: true })}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition-colors">
            <Plus size={16} /> New View
          </button>
        </div>

        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input value={q} onChange={e => setQ(e.target.value)}
            placeholder="Tìm theo tên, mô tả, thẻ…"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-9 pr-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>

        {loading ? (
          <p className="text-gray-500 text-sm">{MSG.loading}</p>
        ) : views.length === 0 ? (
          <div className="text-center py-20 text-gray-600">
            <p className="text-lg">{MSG.emptyViews}</p>
            <p className="text-sm mt-1">{MSG.emptyViewsHint}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 overflow-y-auto overflow-x-hidden pb-4">
            {views.map(v => (
              <ViewCard key={v.id} view={v}
                onEdit={() => setModal({ open: true, view: v })}
                onDelete={() => handleDelete(v.id)} />
            ))}
          </div>
        )}
      </div>

      {modal.open && (
        <ViewModal
          initial={modal.view
            ? { name: modal.view.name, schema_name: modal.view.schema_name, category: modal.view.category, description: modal.view.description, sql_def: modal.view.sql_def, tags: modal.view.tags }
            : EMPTY}
          onSave={handleSave}
          onClose={() => setModal({ open: false })} />
      )}
    </div>
  )
}
