import { useRef, useState } from 'react'
import { UploadCloud } from 'lucide-react'

interface Props { onFiles: (files: File[]) => void; busy: boolean }

export default function MlMergeDropzone({ onFiles, busy }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [drag, setDrag] = useState(false)

  function handleDrop(e: React.DragEvent) {
    e.preventDefault(); setDrag(false)
    const files = Array.from(e.dataTransfer.files)
    if (files.length) onFiles(files)
  }

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={e => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={handleDrop}
      className={`border border-dashed rounded-lg p-5 text-center cursor-pointer transition
        ${drag ? 'border-data bg-data/5' : 'border-data/30 hover:border-data/60'}`}
    >
      <UploadCloud size={22} className="mx-auto mb-2 text-data" />
      <p className="text-xs text-gray-300">
        {busy ? 'Đang đọc file với Polars…' : 'Kéo-thả hoặc bấm để chọn nhiều file (CSV, XLSX)'}
      </p>
      <input
        ref={inputRef} type="file" multiple accept=".csv,.xlsx,.xls" className="hidden"
        onChange={e => {
          const files = Array.from(e.target.files ?? [])
          if (files.length) onFiles(files)
          e.target.value = ''
        }}
      />
    </div>
  )
}
