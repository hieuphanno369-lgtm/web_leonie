import { Plus } from 'lucide-react'
import type { QuickNote } from '../../types'
import NoteItem from './NoteItem'

interface Props {
  notes: QuickNote[]
  selectedId: string | null
  dateFrom: string
  dateTo: string
  category: string
  onSelect: (id: string) => void
  onNew: () => void
  onDateFromChange: (v: string) => void
  onDateToChange: (v: string) => void
  onCategoryChange: (v: string) => void
}

const CATEGORIES = ['', 'daily', 'meeting', 'idea', 'bug']

export default function NoteList({
  notes, selectedId, dateFrom, dateTo, category,
  onSelect, onNew, onDateFromChange, onDateToChange, onCategoryChange,
}: Props) {
  return (
    <div className="w-[340px] border-r border-white/5 flex flex-col flex-shrink-0 h-full">
      {/* Header */}
      <div className="px-4 pt-3.5 pb-2.5 border-b border-white/5">
        <div className="flex items-center justify-between mb-2.5">
          <h2 className="text-sm font-semibold text-white">Quick Notes</h2>
          <button onClick={onNew} className="btn-primary flex items-center gap-1 text-xs px-2.5 py-1">
            <Plus size={12} /> New
          </button>
        </div>
        {/* Date filter */}
        <div className="flex items-center gap-1.5 mb-1.5">
          <input
            type="date"
            value={dateFrom}
            onChange={e => onDateFromChange(e.target.value)}
            className="input-base text-[11px] flex-1 px-2 py-1"
          />
          <span className="text-gray-600 text-xs">→</span>
          <input
            type="date"
            value={dateTo}
            onChange={e => onDateToChange(e.target.value)}
            className="input-base text-[11px] flex-1 px-2 py-1"
          />
        </div>
        {/* Category filter */}
        <select
          value={category}
          onChange={e => onCategoryChange(e.target.value)}
          className="input-base text-[11px] w-full px-2 py-1"
        >
          <option value="">All categories</option>
          {CATEGORIES.filter(Boolean).map(c => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-2 pb-3 pt-1">
        {notes.length === 0 ? (
          <p className="text-center text-gray-600 text-xs mt-8">No notes found</p>
        ) : (
          notes.map(note => (
            <NoteItem
              key={note.id}
              note={note}
              isSelected={note.id === selectedId}
              onSelect={() => onSelect(note.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}
