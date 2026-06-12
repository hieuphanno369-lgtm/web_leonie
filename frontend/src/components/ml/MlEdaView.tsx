import { useState } from 'react'
import type { DatasetInfo, EdaReport } from '../../types'
import { runEda } from '../../api/ml'
import CorrelationHeatmap from './CorrelationHeatmap'
import MlEdaProfile from './MlEdaProfile'
import MlEdaDistribution from './MlEdaDistribution'
import MlEdaSegments from './MlEdaSegments'
import MlEdaInsights from './MlEdaInsights'

export default function MlEdaView({ dataset }: { dataset: DatasetInfo }) {
  const [report, setReport] = useState<EdaReport | null>(null)
  const [busy, setBusy]     = useState(false)
  const [error, setError]   = useState('')

  async function generate() {
    setBusy(true); setError('')
    try {
      setReport(await runEda(dataset.file_id))
    } catch (e) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? 'Không tạo được báo cáo EDA')
    } finally { setBusy(false) }
  }

  return (
    <div className="p-4 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-gray-200">Auto-EDA</h2>
          <p className="text-xs text-gray-500">
            Hồ sơ dữ liệu · tương quan · phân phối · nhóm · insight Finding→So-what→Action.
          </p>
        </div>
        <button onClick={generate} disabled={busy}
          className="rounded-md bg-data px-4 py-2 text-xs font-medium text-black disabled:opacity-40">
          {busy ? 'Đang phân tích…' : 'Tạo báo cáo'}
        </button>
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      {report && (
        <div className="space-y-6">
          <section><MlEdaInsights report={report} /></section>
          <section>
            <h3 className="text-xs font-semibold text-gray-300 mb-2">Hồ sơ cột</h3>
            <MlEdaProfile columns={report.profile} />
          </section>
          <section>
            <h3 className="text-xs font-semibold text-gray-300 mb-2">Tương quan</h3>
            <CorrelationHeatmap data={report.correlation} />
          </section>
          <section>
            <h3 className="text-xs font-semibold text-gray-300 mb-2">Phân phối</h3>
            <MlEdaDistribution dists={report.distributions} />
          </section>
          <section>
            <h3 className="text-xs font-semibold text-gray-300 mb-2">Phân tích nhóm</h3>
            <MlEdaSegments segments={report.segments} />
          </section>
        </div>
      )}
    </div>
  )
}
