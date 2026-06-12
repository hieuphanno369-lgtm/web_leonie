import type { SemanticType } from '../../../types'

interface Props {
  included: string[]
  semanticTypes: Record<string, SemanticType>
  dedupKey: string | null
  requiredFields: string[]
  dropInvalidKey: boolean
  coalesce: boolean
  onDedupKey: (k: string | null) => void
  onToggleRequired: (f: string) => void
  onDropInvalidKey: (v: boolean) => void
  onCoalesce: (v: boolean) => void
}

export default function MergeCleanStep({
  included, semanticTypes, dedupKey, requiredFields,
  dropInvalidKey, coalesce, onDedupKey, onToggleRequired,
  onDropInvalidKey, onCoalesce,
}: Props) {
  return (
    <div className="space-y-4 max-w-xl">
      <div>
        <label className="block text-[11px] uppercase tracking-wide text-gray-600 mb-1">
          Khóa loại trùng (dedup key)
        </label>
        <select
          value={dedupKey ?? ''}
          onChange={e => onDedupKey(e.target.value || null)}
          className="input-base text-xs py-1.5">
          <option value="">— không loại trùng —</option>
          {included.map(f => (
            <option key={f} value={f}>{f} ({semanticTypes[f] ?? 'text'})</option>
          ))}
        </select>
        <p className="text-[10px] text-gray-600 mt-1">
          Các dòng cùng khóa sẽ được gộp lại, lấy giá trị đầy đủ nhất ở mỗi cột.
        </p>
      </div>

      <div>
        <p className="text-[11px] uppercase tracking-wide text-gray-600 mb-1">
          Field bắt buộc (để tính "đủ thông tin")
        </p>
        <div className="rounded-lg border border-white/5 bg-white/5 p-1">
          {included.map(f => (
            <label key={f} className="flex items-center gap-2 px-2 py-1.5 hover:bg-white/5 rounded cursor-pointer">
              <input type="checkbox" checked={requiredFields.includes(f)}
                onChange={() => onToggleRequired(f)} />
              <span className="text-xs text-gray-200">{f}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="space-y-1.5">
        <label className="flex items-center gap-2 text-xs text-gray-400">
          <input type="checkbox" checked={coalesce} onChange={e => onCoalesce(e.target.checked)} />
          Gộp dòng trùng, lấp ô trống từ bản trùng (coalesce)
        </label>
        <label className="flex items-center gap-2 text-xs text-gray-400">
          <input type="checkbox" checked={dropInvalidKey} onChange={e => onDropInvalidKey(e.target.checked)} />
          Bỏ dòng có khóa rỗng / sai định dạng
        </label>
      </div>
    </div>
  )
}
