import { create } from 'zustand'
import type { DatasetInfo, QueryResult } from '../types'

export type MlTab = 'merge' | 'table' | 'charts' | 'stats' | 'forecast' | 'cohort' | 'eda'

/**
 * ML Studio working state, held outside the React tree so it survives route
 * navigation. MlStudio is a lazy-loaded route that unmounts when the user
 * switches to another page (e.g. Automation); component-local useState was
 * being wiped, so returning to ML Studio reset the uploaded dataset, query
 * result and active tab. Keeping it in a module-level store fixes that — the
 * selected dataset and view are restored on return (the file itself already
 * persists on the backend).
 */
interface MlStudioState {
  dataset: DatasetInfo | null
  result: QueryResult | null
  activeTab: MlTab
  setDataset: (d: DatasetInfo | null) => void
  setResult: (r: QueryResult | null) => void
  setActiveTab: (t: MlTab) => void
  reset: () => void
}

export const useMlStudioStore = create<MlStudioState>((set) => ({
  dataset: null,
  result: null,
  activeTab: 'table',
  setDataset: (dataset) => set({ dataset }),
  setResult: (result) => set({ result }),
  setActiveTab: (activeTab) => set({ activeTab }),
  reset: () => set({ dataset: null, result: null, activeTab: 'table' }),
}))
