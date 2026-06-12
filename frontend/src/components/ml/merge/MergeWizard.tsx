import { useMemo, useState } from 'react'
import type {
  DatasetInfo, MergeStageResult, MergeRunResult, SemanticType, FieldGroupSuggestion,
} from '../../../types'
import { stageMerge, runMerge, downloadRejected, downloadMergedClean } from '../../../api/ml'
import MergeStepUpload from './MergeStepUpload'
import MergeFieldGroups from './MergeFieldGroups'
import MergeUnifySuggestions from './MergeUnifySuggestions'
import MergeTypePicker from './MergeTypePicker'
import MergeCleanStep from './MergeCleanStep'
import MergePreview from './MergePreview'
import MergeOutcome from './MergeOutcome'

interface Props { onDatasetCreated: (d: DatasetInfo) => void }

const STEPS = ['Tải file', 'Gộp & loại', 'Làm sạch', 'Xem & tạo']

function errMsg(e: unknown): string {
  return (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Có lỗi xảy ra'
}

export default function MergeWizard({ onDatasetCreated }: Props) {
  const [step, setStep]       = useState(1)
  const [stage, setStage]     = useState<MergeStageResult | null>(null)
  const [included, setIncluded] = useState<string[]>([])
  const [fieldGroups, setFieldGroups] = useState<Record<string, string[]>>({})
  const [semanticTypes, setSemanticTypes] = useState<Record<string, SemanticType>>({})
  const [dedupKey, setDedupKey] = useState<string | null>(null)
  const [requiredFields, setRequiredFields] = useState<string[]>([])
  const [dropInvalidKey, setDropInvalidKey] = useState(true)
  const [coalesce, setCoalesce] = useState(true)
  const [dry, setDry]         = useState<MergeRunResult | null>(null)
  const [busy, setBusy]       = useState(false)
  const [error, setError]     = useState('')

  // field name (raw or canonical) -> inferred type & samples, from profiles
  const profByName = useMemo(() => {
    const m: Record<string, { type: SemanticType; samples: string[] }> = {}
    stage?.profiles.forEach(p => {
      if (!m[p.name]) m[p.name] = { type: p.inferred_type, samples: p.samples }
    })
    return m
  }, [stage])

  function samplesFor(field: string): string[] {
    if (profByName[field]) return profByName[field].samples
    const members = fieldGroups[field]
    if (members) for (const mem of members) if (profByName[mem]) return profByName[mem].samples
    return []
  }

  async function handleFiles(files: File[]) {
    setBusy(true); setError('')
    try {
      const r = await stageMerge(files, stage?.session_id)
      setStage(r)
      setIncluded(r.common_fields)
      // seed semantic types from profiles (first profile per name wins)
      const st: Record<string, SemanticType> = {}
      r.profiles.forEach(p => { if (!st[p.name]) st[p.name] = p.inferred_type })
      setSemanticTypes(st)
    } catch (e) { setError(errMsg(e)) } finally { setBusy(false) }
  }

  function handleRemove(filename: string) {
    if (!stage) return
    setStage({ ...stage, files: stage.files.filter(f => f.filename !== filename) })
  }

  function toggleInclude(f: string) {
    setIncluded(s => s.includes(f) ? s.filter(x => x !== f) : [...s, f])
  }

  function acceptSuggestion(s: FieldGroupSuggestion) {
    setFieldGroups(g => ({ ...g, [s.canonical]: s.members }))
    setSemanticTypes(t => ({ ...t, [s.canonical]: s.inferred_type }))
    setIncluded(inc => {
      const without = inc.filter(f => !s.members.includes(f))
      return without.includes(s.canonical) ? without : [...without, s.canonical]
    })
  }

  function splitSuggestion(canonical: string) {
    setFieldGroups(g => { const n = { ...g }; delete n[canonical]; return n })
    setIncluded(inc => inc.filter(f => f !== canonical))
  }

  function toggleRequired(f: string) {
    setRequiredFields(s => s.includes(f) ? s.filter(x => x !== f) : [...s, f])
  }

  function buildOptions() {
    return {
      dedup_key: dedupKey, drop_invalid_key: dropInvalidKey, trim: true,
      semantic_types: semanticTypes, field_groups: fieldGroups,
      required_fields: requiredFields, coalesce,
    }
  }

  async function runDry() {
    if (!stage) return
    setBusy(true); setError('')
    try {
      const r = await runMerge(stage.session_id, included, {}, buildOptions(), true)
      setDry(r)
    } catch (e) { setError(errMsg(e)) } finally { setBusy(false) }
  }

  async function createDataset() {
    if (!stage) return
    setBusy(true); setError('')
    try {
      const r = await runMerge(stage.session_id, included, {}, buildOptions(), false)
      if (r.dataset) onDatasetCreated(r.dataset)
    } catch (e) { setError(errMsg(e)) } finally { setBusy(false) }
  }

  function goTo(next: number) {
    setError('')
    if (next === 4) { setStep(4); runDry() } else setStep(next)
  }

  return (
    <div className="p-4 max-w-4xl space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-gray-200 mb-1">Combine file</h2>
        <div className="flex gap-1.5">
          {STEPS.map((label, i) => (
            <div key={label}
              className={`flex-1 text-center text-[11px] py-1 rounded ${
                step === i + 1 ? 'bg-data/20 text-data' : 'bg-white/5 text-gray-500'}`}>
              {i + 1}. {label}
            </div>
          ))}
        </div>
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      {step === 1 && (
        <MergeStepUpload stage={stage} busy={busy}
          onFiles={handleFiles} onRemove={handleRemove} onNext={() => goTo(2)} />
      )}

      {step === 2 && stage && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <MergeFieldGroups stage={stage} included={included} onToggle={toggleInclude} />
            <MergeUnifySuggestions
              suggestions={stage.suggestions} accepted={fieldGroups}
              onAccept={acceptSuggestion} onSplit={splitSuggestion} />
          </div>
          <MergeTypePicker included={included} semanticTypes={semanticTypes}
            samplesFor={samplesFor}
            onChange={(f, t) => setSemanticTypes(s => ({ ...s, [f]: t }))} />
          <div className="flex justify-between">
            <button onClick={() => goTo(1)} className="text-xs text-gray-500 hover:text-gray-300">← Quay lại</button>
            <button onClick={() => goTo(3)} disabled={included.length === 0}
              className="rounded-md bg-data px-4 py-2 text-xs font-medium text-black disabled:opacity-40">
              Tiếp tục →
            </button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-4">
          <MergeCleanStep included={included} semanticTypes={semanticTypes}
            dedupKey={dedupKey} requiredFields={requiredFields}
            dropInvalidKey={dropInvalidKey} coalesce={coalesce}
            onDedupKey={setDedupKey} onToggleRequired={toggleRequired}
            onDropInvalidKey={setDropInvalidKey} onCoalesce={setCoalesce} />
          <div className="flex justify-between">
            <button onClick={() => goTo(2)} className="text-xs text-gray-500 hover:text-gray-300">← Quay lại</button>
            <button onClick={() => goTo(4)}
              className="rounded-md bg-data px-4 py-2 text-xs font-medium text-black">
              Xem trước →
            </button>
          </div>
        </div>
      )}

      {step === 4 && (
        <div className="space-y-4">
          {busy && <p className="text-xs text-gray-500">Đang tính toán…</p>}
          {dry && (
            <>
              <MergeOutcome summary={dry.summary} code={dry.code}
                onDownloadRejected={() => stage && downloadRejected(stage.session_id)}
                onExport={fmt => stage && downloadMergedClean(stage.session_id, fmt)} />
              <div>
                <p className="text-[11px] uppercase tracking-wide text-gray-600 mb-1.5">Xem trước (30 dòng)</p>
                <MergePreview rows={dry.preview ?? []} />
              </div>
            </>
          )}
          <div className="flex justify-between">
            <button onClick={() => goTo(3)} className="text-xs text-gray-500 hover:text-gray-300">← Quay lại</button>
            <button onClick={createDataset} disabled={busy || !dry}
              className="rounded-md bg-success px-4 py-2 text-xs font-medium text-black disabled:opacity-40">
              {busy ? 'Đang tạo…' : 'Tạo dataset'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
