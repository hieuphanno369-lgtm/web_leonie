import { Tag, Link2 } from 'lucide-react'
import type { QuickNote } from '../../types'

const CATEGORY_STYLES: Record<string, string> = {
  daily:   'text-green-400 bg-green-400/10 border-green-400/20',
  meeting: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20',
  idea:    'text-purple-400 bg-purple-400/10 border-purple-400/20',
  bug:     'text-red-400 bg-red-400/10 border-red-400/20',
}

interface Props {
  note: QuickNote
  isSelected: boolean
  onSelect: () => void
}

export default function NoteItem({ note, isSelected, onSelect }: Props) {
  const categoryStyle = note.category
    ? (CATEGORY_STYLES[note.category] ?? 'text-gray-400 bg-gray-400/10 border-gray-400/20')
    : null

  const preview = note.title
    ?? (note.content.length > 60 ? note.content.slice(0, 60) + '…' : note.content)

  return (
    <button
      onClick={onSelect}
      className={`w-full text-left px-3 py-2.5 rounded-lg mb-1 transition-all ${
        isSelected
          ? 'bg-white/5 border border-white/10'
          : 'hover:bg-white/5 border border-transparent'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm text-white truncate flex-1">{preview}</p>
        {(note.task_id || note.eda_id) && (
          <Link2 size={11} className="text-gray-500 mt-0.5 flex-shrink-0" />
        )}
      </div>
      <div className="flex items-center gap-2 mt-1">
        <span className="text-[11px] text-gray-500 font-mono">{note.date}</span>
        {note.category && categoryStyle && (
          <span className={`flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded border ${categoryStyle}`}>
            <Tag size={9} />
            {note.category}
          </span>
        )}
      </div>
    </button>
  )
}
