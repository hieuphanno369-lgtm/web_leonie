import type { SemanticType, ColumnProfile } from '../../../types'

const TYPES: SemanticType[] = ['phone', 'email', 'date', 'number', 'category', 'text']

interface Props {
  included: string[]                          // canonical fields user is keeping
  semanticTypes: Record<string, SemanticType>
  samplesFor: (field: string) => string[]     // resolved from profiles
  onChange: (field: string, t: SemanticType) => void
}

export default function MergeTypePicker({ included, semanticTypes, samplesFor, onChange }: Props) {
  if (included.length === 0) {
    return <p className="text-[11px] text-gray-600">Chọn field để xác nhận loại dữ liệu.</p>
  }
  return (
    <div className="space-y-2">
      <p className="text-[11px] uppercase tracking-wide text-gray-600">
        Xác nhận loại dữ liệu
      </p>
      {included.map(f => {
        const samples = samplesFor(f).slice(0, 4)
        return (
          <div key={f} className="rounded-lg border border-white/5 bg-white/5 p-2.5">
            <div className="flex items-center justify-between gap-2 mb-1">
              <span className="text-xs font-medium text-gray-100 truncate">{f}</span>
              <select
                value={semanticTypes[f] ?? 'text'}
                onChange={e => onChange(f, e.target.value as SemanticType)}
                className="input-base text-[11px] py-1 px-2 w-28">
                {TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            {samples.length > 0 && (
              <p className="text-[10px] text-gray-500 truncate">vd: {samples.join(' · ')}</p>
            )}
          </div>
        )
      })}
    </div>
  )
}

export type { ColumnProfile }
