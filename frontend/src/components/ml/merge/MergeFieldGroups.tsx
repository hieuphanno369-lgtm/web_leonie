import type { MergeStageResult } from '../../../types'

interface Props {
  stage: MergeStageResult
  included: string[]
  onToggle: (field: string) => void
}

// Count how many files contain a field (by raw name) + which files.
function filesFor(stage: MergeStageResult, field: string): string[] {
  return stage.files.filter(f => f.fields.includes(field)).map(f => f.filename)
}

export default function MergeFieldGroups({ stage, included, onToggle }: Props) {
  const n = stage.files.length
  const common = new Set(stage.common_fields)
  const commonFields = stage.all_fields.filter(f => common.has(f))
  const individual = stage.all_fields.filter(f => !common.has(f))

  const Row = ({ field }: { field: string }) => {
    const owners = filesFor(stage, field)
    return (
      <label title={owners.join(', ')}
        className="flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-white/5 cursor-pointer">
        <input type="checkbox" checked={included.includes(field)} onChange={() => onToggle(field)} />
        <span className="text-xs text-gray-200 truncate flex-1">{field}</span>
        <span className="text-[10px] text-gray-500 flex-shrink-0">{owners.length}/{n} file</span>
      </label>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div>
        <p className="text-[11px] uppercase tracking-wide text-gray-600 mb-1.5">
          Field chung (mọi file)
        </p>
        <div className="rounded-lg border border-white/5 bg-white/5 p-1">
          {commonFields.length === 0
            ? <p className="text-[11px] text-gray-600 px-2 py-2">Không có field chung</p>
            : commonFields.map(f => <Row key={f} field={f} />)}
        </div>
      </div>
      <div>
        <p className="text-[11px] uppercase tracking-wide text-gray-600 mb-1.5">
          Field riêng lẻ
        </p>
        <div className="rounded-lg border border-white/5 bg-white/5 p-1 max-h-72 overflow-y-auto">
          {individual.length === 0
            ? <p className="text-[11px] text-gray-600 px-2 py-2">Tất cả field đều chung</p>
            : individual.map(f => <Row key={f} field={f} />)}
        </div>
      </div>
    </div>
  )
}
