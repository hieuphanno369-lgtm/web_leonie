import { BarChart2, Table, FlaskConical, TrendingUp, Users, Upload, Combine, Telescope } from 'lucide-react'
import type { DatasetInfo, QueryResult, QualityResult } from '../../types'
import MlChartView    from './MlChartView'
import MlTableView    from './MlTableView'
import MlStatsView    from './MlStatsView'
import MlForecastView from './MlForecastView'
import MlCohortView   from './MlCohortView'
import MergeWizard    from './merge/MergeWizard'
import MlEdaView      from './MlEdaView'
import { MSG } from '../../messages'

type Tab = 'merge' | 'table' | 'charts' | 'stats' | 'forecast' | 'cohort' | 'eda'

interface Props {
  result: QueryResult | null
  dataset: DatasetInfo | null
  activeTab: Tab
  onTabChange: (t: Tab) => void
  quality: QualityResult | null
  qualityError?: boolean
  datasets: DatasetInfo[]
  onDatasetCreated: (d: DatasetInfo) => void
}

const TABS: { key: Tab; label: string; Icon: React.ElementType }[] = [
  { key: 'table',    label: 'Table',        Icon: Table        },
  { key: 'charts',   label: 'Charts',       Icon: BarChart2    },
  { key: 'stats',    label: 'Stats',        Icon: FlaskConical },
  { key: 'forecast', label: 'Forecast',     Icon: TrendingUp   },
  { key: 'cohort',   label: 'Cohort',       Icon: Users        },
  { key: 'merge',    label: 'Combine file', Icon: Combine      },
  { key: 'eda',      label: 'Auto-EDA',     Icon: Telescope    },
]

function Empty({ text }: { text: string }) {
  return (
    <div className="flex items-center justify-center h-full text-gray-600 text-sm">
      {text}
    </div>
  )
}

// What ML Studio can do — shown on the onboarding empty-state so a first-time
// user discovers the analysis/forecast power instead of facing a blank panel.
const STUDIO_FEATURES: { Icon: React.ElementType; label: string; desc: string }[] = [
  { Icon: FlaskConical, label: 'Stats & Quality', desc: 'Describe columns, spot outliers (box plot, z-score)' },
  { Icon: Table,        label: 'SQL Query',       desc: 'Slice & shape your data with DuckDB SQL' },
  { Icon: BarChart2,    label: 'Charts',          desc: 'Distributions, correlations, comparisons' },
  { Icon: TrendingUp,   label: 'Forecast',        desc: 'Project trends forward from your data' },
  { Icon: Users,        label: 'Cohort',          desc: 'Compare groups & retention over time' },
]

function EmptyStudio() {
  return (
    <div className="flex-1 flex items-center justify-center h-full p-8 overflow-auto">
      <div className="max-w-lg w-full text-center">
        <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-data/10 border border-data/20 flex items-center justify-center">
          <FlaskConical size={26} className="text-data" />
        </div>
        <h2 className="text-xl font-semibold text-white mb-1.5">Welcome to ML Studio</h2>
        <p className="text-gray-400 text-sm mb-6">
          {MSG.mlUploadHint}
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-left">
          {STUDIO_FEATURES.map(({ Icon, label, desc }) => (
            <div key={label} className="flex items-start gap-2.5 px-3 py-2.5 rounded-lg bg-white/5 border border-white/5">
              <Icon size={16} className="text-data mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-xs font-medium text-gray-200 leading-tight">{label}</p>
                <p className="text-[11px] text-gray-500 mt-0.5 leading-snug">{desc}</p>
              </div>
            </div>
          ))}
        </div>
        <p className="text-[11px] text-gray-600 mt-5 flex items-center justify-center gap-1.5">
          <Upload size={12} /> Start by uploading a dataset in the left panel
        </p>
      </div>
    </div>
  )
}

export default function MlResultTabs({ result, dataset, activeTab, onTabChange, quality, qualityError, datasets, onDatasetCreated }: Props) {
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="flex border-b border-white/5 flex-shrink-0">
        {TABS.map(({ key, label, Icon }) => (
          <button
            key={key}
            onClick={() => onTabChange(key)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-all ${
              activeTab === key
                ? 'border-data text-data'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            <Icon size={12} /> {label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto relative">
        {/* Merge works with no dataset — it CREATES one */}
        <div className={activeTab === 'merge' ? '' : 'hidden'}>
          <MergeWizard onDatasetCreated={onDatasetCreated} />
        </div>

        {/* Every other tab needs a dataset — show onboarding until one exists */}
        {activeTab !== 'merge' && !dataset && <EmptyStudio />}

        {activeTab !== 'merge' && dataset && (
          <>
            <div className={activeTab === 'table'    ? '' : 'hidden'}>
              {result ? <MlTableView result={result} /> : <Empty text={MSG.runToSeeResults} />}
            </div>
            <div className={activeTab === 'charts'   ? '' : 'hidden'}>
              {result ? <MlChartView result={result} dataset={dataset} quality={quality} qualityError={qualityError} /> : <Empty text={MSG.runToSeeCharts} />}
            </div>
            <div className={activeTab === 'stats'    ? '' : 'hidden'}>
              <MlStatsView dataset={dataset} quality={quality} qualityError={qualityError} />
            </div>
            <div className={activeTab === 'forecast' ? '' : 'hidden'}>
              <MlForecastView dataset={dataset} quality={quality} qualityError={qualityError} />
            </div>
            <div className={activeTab === 'cohort'   ? '' : 'hidden'}>
              <MlCohortView dataset={dataset} datasets={datasets} quality={quality} qualityError={qualityError} />
            </div>
            <div className={activeTab === 'eda'      ? '' : 'hidden'}>
              <MlEdaView dataset={dataset} />
            </div>
          </>
        )}
      </div>
    </div>
  )
}
