import { Pencil, Trash2, Tag, Link2 } from 'lucide-react'
import type { QuickNote } from '../../types'

const CATEGORY_STYLES: Record<string, string> = {
  daily:   'text-green-400 bg-green-400/10 border-green-400/20',
  meeting: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20',
  idea:    'text-purple-400 bg-purple-400/10 border-purple-400/20',
  bug:     'text-red-400 bg-red-400/10 border-red-400/20',
}

interface Props {
  note: QuickNote
  taskTitle?: string | null
  edaTitle?: string | null
  onEdit: () => void
  onDelete: (id: string) => void
}

export default function NoteDetail({ note, taskTitle, edaTitle, onEdit, onDelete }: Props) {
  const categoryStyle = note.category
    ? (CATEGORY_STYLES[note.category] ?? 'text-gray-400 bg-gray-400/10 border-gray-400/20')
    : null

  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="px-5 pt-4 pb-3 border-b border-white/5 flex items-start justify-between flex-shrink-0">
        <div className="flex-1 min-w-0">
          {note.title && (
            <h2 className="text-base font-semibold text-white mb-1 truncate">{note.title}</h2>
          )}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] text-gray-400 font-mono">{note.date}</span>
            {note.category && categoryStyle && (
              <span className={`flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded border ${categoryStyle}`}>
                <Tag size={9} />
                {note.category}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 ml-3 flex-shrink-0">
          <button
            onClick={onEdit}
            className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-all"
            title="Edit"
          >
            <Pencil size={14} />
          </button>
          <button
            onClick={() => onDelete(note.id)}
            className="p-1.5 rounded-lg text-gray-400 hover:text-danger hover:bg-danger/10 transition-all"
            title="Delete"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="px-5 py-4 flex-1">
        <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">
          {note.content}
        </p>
      </div>

      {/* Linked item */}
      {(taskTitle || edaTitle) && (
        <div className="px-5 py-3 border-t border-white/5 flex-shrink-0">
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <Link2 size={12} />
            <span>{taskTitle ? `Task: ${taskTitle}` : `EDA: ${edaTitle}`}</span>
          </div>
        </div>
      )}
    </div>
  )
}
