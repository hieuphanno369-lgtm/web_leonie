import { useState, useCallback, useEffect, useRef } from 'react'
import type { DatasetInfo, QualityResult } from '../../types'
import { uploadFile, deleteDataset, runQuery, fetchQuality, fetchDatasets } from '../../api/ml'
import { useMlStudioStore } from '../../stores/mlStudioStore'
import MlUpload        from '../../components/ml/MlUpload'
import MlResultTabs    from '../../components/ml/MlResultTabs'
import MlDescribePanel from '../../components/ml/MlDescribePanel'
import { useResizableSidebar, ResizeHandle } from '../../components/layout/ResizableSidebar'
import { MSG } from '../../messages'

export default function MlStudio() {
  // dataset / result / activeTab live in a module-level store so they survive
  // this lazy route being unmounted when the user navigates to another page and
  // back — component-local useState was wiped, so the uploaded dataset was "lost".
  const dataset      = useMlStudioStore(s => s.dataset)
  const setDataset   = useMlStudioStore(s => s.setDataset)
  const result       = useMlStudioStore(s => s.result)
  const setResult    = useMlStudioStore(s => s.setResult)
  const activeTab    = useMlStudioStore(s => s.activeTab)
  const setActiveTab = useMlStudioStore(s => s.setActiveTab)

  const [uploading, setUploading] = useState(false)
  const [running,   setRunning]   = useState(false)
  const [sqlError,  setSqlError]  = useState('')
  const [apiError,  setApiError]  = useState('')
  const [qualityCache, setQualityCache] = useState<Record<string, QualityResult>>({})
  const [qualityErrors, setQualityErrors] = useState<Set<string>>(new Set())
  const [datasets, setDatasets] = useState<DatasetInfo[]>([])
  const fetchedRef = useRef<Set<string>>(new Set())
  const { width: sidebarWidth, onDragStart } = useResizableSidebar({
    initial: 280, min: 240, max: 620, storageKey: 'leonie:ml-sidebar-w',
  })

  const refreshDatasets = useCallback(async () => {
    try {
      const list = await fetchDatasets()
      setDatasets(list)
      return list
    } catch { return null }
  }, [])

  // On mount: refresh the dataset list, and drop any persisted selection that no
  // longer exists server-side (file deleted / DB reset while away) so a stale
  // dataset can't 404 on the next query.
  useEffect(() => {
    refreshDatasets().then(list => {
      if (!list) return
      const cur = useMlStudioStore.getState().dataset
      if (cur && !list.some(d => d.file_id === cur.file_id)) {
        useMlStudioStore.getState().reset()
      }
    })
  }, [refreshDatasets])

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true); setApiError('')
    try {
      setDataset(await uploadFile(file))
      setResult(null)
      refreshDatasets()
    } catch (e: unknown) {
      setApiError(
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? MSG.uploadFailed
      )
    }
    finally { setUploading(false) }
  }, [])

  function handleDatasetCreated(d: DatasetInfo) {
    setDataset(d)
    setResult(null)
    refreshDatasets()
    setActiveTab('eda')   // land on Auto-EDA so the user immediately profiles the merge
  }

  async function handleClear() {
    if (dataset) {
      try { await deleteDataset(dataset.file_id) } catch { /* ignore */ }
    }
    setDataset(null); setResult(null); setSqlError('')
    refreshDatasets()
  }

  async function handleRun(sql: string) {
    if (!dataset) return
    setRunning(true); setSqlError(''); setResult(null)
    try {
      setResult(await runQuery(dataset.file_id, sql))
      setActiveTab('table')
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setSqlError(detail ?? MSG.queryFailed)
    } finally { setRunning(false) }
  }

  useEffect(() => {
    const fid = dataset?.file_id
    if (!fid || fetchedRef.current.has(fid)) return
    fetchedRef.current.add(fid)
    fetchQuality(fid)
      .then(result => setQualityCache(prev => ({ ...prev, [fid]: result })))
      .catch(() => {
        setQualityErrors(prev => new Set([...prev, fid]))
      })
  }, [dataset?.file_id])

  const quality = dataset ? (qualityCache[dataset.file_id] ?? null) : null
  const qualityError = dataset ? qualityErrors.has(dataset.file_id) : false

  return (
    <div className="flex h-screen overflow-hidden">
      <div style={{ width: sidebarWidth }} className="border-r border-white/5 flex flex-col gap-4 p-4 flex-shrink-0 overflow-y-auto">
        <h2 className="text-sm font-semibold text-white">ML Studio</h2>
        {apiError && <p className="text-danger text-xs">{apiError}</p>}
        <MlUpload
          dataset={dataset}
          uploading={uploading}
          onUpload={handleUpload}
          onClear={handleClear}
        />
        {dataset && (
          <MlDescribePanel
            dataset={dataset}
            running={running}
            sqlError={sqlError}
            onRun={handleRun}
          />
        )}
      </div>

      <ResizeHandle onDragStart={onDragStart} color="analytics" />

      <MlResultTabs
        result={result}
        dataset={dataset}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        quality={quality}
        qualityError={qualityError}
        datasets={datasets}
        onDatasetCreated={handleDatasetCreated}
      />
    </div>
  )
}
