import { useRef } from 'react'
import { Upload, Trash2 } from 'lucide-react'
import type { DatasetInfo } from '../../types'

interface Props {
  dataset: DatasetInfo | null
  uploading: boolean
  onUpload: (file: File) => void
  onClear: () => void
}

export default function MlUpload({ dataset, uploading, onUpload, onClear }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) onUpload(file)
  }

  return (
    <div className="flex flex-col gap-3">
      {!dataset ? (
        <div
          onDrop={handleDrop}
          onDragOver={e => e.preventDefault()}
          onClick={() => inputRef.current?.click()}
          className="border border-dashed border-data/30 rounded-lg p-5 text-center cursor-pointer hover:border-data/50 hover:bg-data/3 transition-all"
        >
          <input
            ref={inputRef} type="file" accept=".csv,.xlsx,.xls"
            className="hidden"
            onChange={e => { const f = e.target.files?.[0]; if (f) onUpload(f) }}
          />
          {uploading ? (
            <div className="flex flex-col items-center gap-2">
              <div className="w-5 h-5 border-2 border-data/30 border-t-data rounded-full animate-spin" />
              <p className="text-data text-xs">Reading with Polars...</p>
            </div>
          ) : (
            <>
              <Upload size={22} className="text-data mx-auto mb-2 opacity-60" />
              <p className="text-gray-400 text-xs">Drop CSV / Excel</p>
              <p className="text-gray-600 text-[10px] mt-1">Polars · max 500 MB</p>
            </>
          )}
        </div>
      ) : (
        <div className="bg-secondary border border-white/5 rounded-lg p-3">
          <div className="flex items-start justify-between gap-2 mb-2">
            <p className="text-white text-xs font-semibold truncate">{dataset.filename}</p>
            <button onClick={onClear} className="text-gray-600 hover:text-danger flex-shrink-0">
              <Trash2 size={12} />
            </button>
          </div>
          <p className="text-gray-600 text-[10px] mb-2">
            {dataset.rows.toLocaleString()} rows · {dataset.cols} cols
          </p>
          <div className="flex flex-wrap gap-1 max-h-16 overflow-hidden">
            {dataset.columns.slice(0, 8).map(c => (
              <span key={c.name} className="bg-data/10 text-data text-[9px] px-1.5 py-0.5 rounded">
                {c.name}
              </span>
            ))}
            {dataset.columns.length > 8 && (
              <span className="text-gray-600 text-[9px]">+{dataset.columns.length - 8} more</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
