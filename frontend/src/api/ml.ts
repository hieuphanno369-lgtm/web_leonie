import client from './client'
import type {
  DatasetInfo, QueryResult, StatsResult, ForecastResult,
  ForecastCompareResult, ForecastInterpretResult, CorrelationMatrix, QualityResult,
  ZScoreData, BoxPlotData, TimeseriesResult, ProfileResult, DrilldownResult,
  MergeStageResult, MergeRunResult, MergeOptions, EdaReport,
} from '../types'

export async function uploadFile(file: File): Promise<DatasetInfo> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await client.post<DatasetInfo>('/ml/upload', form, {
    headers: { 'Content-Type': undefined },
    timeout: 120_000,
  })
  return data
}

export async function fetchDatasets(): Promise<DatasetInfo[]> {
  const { data } = await client.get<DatasetInfo[]>('/ml/datasets')
  return data
}

export async function deleteDataset(file_id: string): Promise<void> {
  await client.delete(`/ml/${file_id}`)
}

export async function runQuery(file_id: string, sql: string): Promise<QueryResult> {
  const { data } = await client.post<QueryResult>('/ml/query', { file_id, sql })
  return data
}

export async function runStats(
  file_id: string, test: string, col_a: string, col_b?: string
): Promise<StatsResult> {
  const { data } = await client.post<StatsResult>('/ml/stats', { file_id, test, col_a, col_b })
  return data
}

export async function runForecast(
  file_id: string, date_col: string, value_col: string,
  periods: number, method: string, seasonal_period: number | null = null,
  grain = 'auto', agg = 'sum',
): Promise<ForecastResult> {
  const { data } = await client.post<ForecastResult>('/ml/forecast', {
    file_id, date_col, value_col, periods, method, seasonal_period, grain, agg,
  })
  return data
}

export async function fetchCorrelation(file_id: string): Promise<CorrelationMatrix> {
  const { data } = await client.get<CorrelationMatrix>(`/ml/${file_id}/correlation`)
  return data
}

export async function runTimeseries(
  file_id: string, date_col: string, value_col: string,
  grain: string, agg: string, comparisons: string[],
  rolling_window = 7, cumulative_reset = 'year',
): Promise<TimeseriesResult> {
  const { data } = await client.post<TimeseriesResult>('/ml/timeseries', {
    file_id, date_col, value_col, grain, agg, comparisons,
    rolling_window, cumulative_reset,
  })
  return data
}

export async function fetchProfile(file_id: string): Promise<ProfileResult> {
  const { data } = await client.get<ProfileResult>(`/ml/profile/${file_id}`)
  return data
}

export interface DescribeRow {
  col: string
  dtype: string
  nulls: number
  min?: number
  max?: number
  mean?: number
  median?: number
  range?: number
  std?: number
}

export interface DescribeResult {
  rows: DescribeRow[]
  code: string
}

export async function fetchDescribe(file_id: string): Promise<DescribeResult> {
  const { data } = await client.get<DescribeResult>(`/ml/${file_id}/describe`)
  return data
}

export async function fetchDrilldown(
  file_id: string, date_col: string, value_col: string,
  agg: string, grain: 'year' | 'month' | 'day',
  year?: number, month?: number,
): Promise<DrilldownResult> {
  const { data } = await client.get<DrilldownResult>(`/ml/${file_id}/drilldown`, {
    params: { date_col, value_col, agg, grain, year, month },
  })
  return data
}

export interface CohortResult {
  cohorts:         string[]
  periods:         number[]
  matrix:          (number | null)[][]
  cohort_sizes:    number[]
  all_users_row?:  (number | null)[]
  all_users_size?: number
  // suitability-gate shape (transactional mode, unsuitable data → HTTP 200):
  suitable?:       boolean
  reasons?:        string[]
  needs?:          string
  role_hint?:      { date: string; user: string }
  code?:           string
}

export async function runCohort(
  file_id: string, date_col: string, user_col: string,
  period: 'day' | 'week' | 'month' | 'quarter' | 'year',
  filter_col?: string, filter_val?: string,
  offset_col?: string, metric_col?: string,
): Promise<CohortResult> {
  const { data } = await client.post<CohortResult>('/ml/cohort', {
    file_id, date_col, user_col, period, filter_col, filter_val, offset_col, metric_col,
  })
  return data
}

export async function fetchColumnValues(file_id: string, col: string, signal?: AbortSignal): Promise<string[]> {
  const { data } = await client.get<{ values: string[] }>(`/ml/${file_id}/column-values`, { params: { col }, signal })
  return data.values
}

export interface StatsInterpretation {
  numbers: string
  insights: string
  actions: string
}

export async function interpretStats(
  test: string, col_a: string, col_b: string | undefined,
  result: Record<string, unknown>, filename: string,
): Promise<StatsInterpretation> {
  const { data } = await client.post<StatsInterpretation>('/ml/stats/interpret', {
    test, col_a, col_b, result, filename,
  })
  return data
}

export async function compareForecast(
  file_id: string,
  date_col: string,
  value_col: string,
  periods: number,
  seasonal_period: number,
  methods: string[],
): Promise<ForecastCompareResult> {
  const { data } = await client.post<ForecastCompareResult>('/ml/forecast/compare', {
    file_id, date_col, value_col, periods, seasonal_period, methods,
  })
  return data
}

export async function interpretForecast(body: {
  method: string
  date_col: string
  value_col: string
  periods: number
  result: object
  filename: string
}): Promise<ForecastInterpretResult> {
  const { data } = await client.post<ForecastInterpretResult>('/ml/forecast/interpret', body)
  return data
}

export async function fetchQuality(file_id: string): Promise<QualityResult> {
  const { data } = await client.get<QualityResult>(`/ml/quality/${file_id}`)
  return data
}

export async function runZScore(
  file_id: string, col_a: string
): Promise<ZScoreData> {
  const { data } = await client.post<ZScoreData>('/ml/stats', {
    file_id, test: 'zscore', col_a,
  })
  return data
}

export async function downloadZScoreCsv(
  fileId: string, colA: string
): Promise<void> {
  const { data } = await client.post(
    '/ml/stats/zscore_csv',
    { file_id: fileId, col_a: colA },
    { responseType: 'blob' },
  )
  const url = URL.createObjectURL(new Blob([data as BlobPart], { type: 'text/csv' }))
  const a   = document.createElement('a')
  a.href     = url
  a.download = `zscore_${colA}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export async function runBoxPlot(
  file_id: string, col_a: string,
  col_b?: string, max_groups: number = 10,
): Promise<BoxPlotData> {
  const { data } = await client.post<BoxPlotData>('/ml/stats', {
    file_id, test: 'boxplot', col_a, col_b, max_groups,
  })
  return data
}

export async function downloadBoxOutliersCsv(
  fileId: string, colA: string, colB?: string, maxGroups: number = 10,
): Promise<void> {
  const { data } = await client.post(
    '/ml/stats/boxplot_outliers_csv',
    { file_id: fileId, col_a: colA, col_b: colB, max_groups: maxGroups },
    { responseType: 'blob' },
  )
  const url = URL.createObjectURL(new Blob([data as BlobPart], { type: 'text/csv' }))
  const a   = document.createElement('a')
  a.href     = url
  a.download = `box_outliers_${colA}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export async function downloadBoxStatsCsv(
  fileId: string, colA: string, colB?: string, maxGroups: number = 10,
): Promise<void> {
  const { data } = await client.post(
    '/ml/stats/boxplot_stats_csv',
    { file_id: fileId, col_a: colA, col_b: colB, max_groups: maxGroups },
    { responseType: 'blob' },
  )
  const url = URL.createObjectURL(new Blob([data as BlobPart], { type: 'text/csv' }))
  const a   = document.createElement('a')
  a.href     = url
  a.download = `box_stats_${colA}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export async function stageMerge(
  files: File[], sessionId?: string, sheet?: string,
): Promise<MergeStageResult> {
  const form = new FormData()
  files.forEach(f => form.append('files', f))
  if (sessionId) form.append('session_id', sessionId)
  if (sheet) form.append('sheet', sheet)
  const { data } = await client.post<MergeStageResult>('/ml/merge/stage', form, {
    headers: { 'Content-Type': undefined }, timeout: 120_000,
  })
  return data
}

export async function runMerge(
  sessionId: string, selectedFields: string[],
  aliasMap: Record<string, string>, options: MergeOptions, dryRun = false,
): Promise<MergeRunResult> {
  const { data } = await client.post<MergeRunResult>('/ml/merge/run', {
    session_id: sessionId, selected_fields: selectedFields,
    alias_map: aliasMap, options, dry_run: dryRun,
  }, { timeout: 120_000 })
  return data
}

export async function deleteMergeSession(sessionId: string): Promise<void> {
  await client.delete(`/ml/merge/${sessionId}`)
}

export async function downloadRejected(sessionId: string): Promise<void> {
  const { data } = await client.get(`/ml/merge/${sessionId}/rejected.csv`, { responseType: 'blob' })
  const url = URL.createObjectURL(new Blob([data as BlobPart], { type: 'text/csv' }))
  const a = document.createElement('a'); a.href = url; a.download = 'rejected.csv'; a.click()
  URL.revokeObjectURL(url)
}

export async function downloadMergedClean(sessionId: string, fmt: 'csv' | 'xlsx'): Promise<void> {
  // Export the cleaned merge result (clean.parquet) — persisted on every /merge/run
  // (dry-run included), so this works straight from the preview step.
  const { data } = await client.get(`/ml/merge/${sessionId}/download`, { params: { fmt }, responseType: 'blob' })
  const mime = fmt === 'csv'
    ? 'text/csv'
    : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  const url = URL.createObjectURL(new Blob([data as BlobPart], { type: mime }))
  const a = document.createElement('a'); a.href = url; a.download = `combined_clean.${fmt}`; a.click()
  URL.revokeObjectURL(url)
}

export async function downloadDataset(fileId: string, fmt: 'csv' | 'xlsx'): Promise<void> {
  // Blob download — mirror downloadZScoreCsv: GET the file as a blob, then click
  // a transient anchor. baseURL is /api, so the path carries only the /ml/ prefix.
  const { data } = await client.get(`/ml/${fileId}/download`, { params: { fmt }, responseType: 'blob' })
  const mime = fmt === 'csv'
    ? 'text/csv'
    : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  const url = URL.createObjectURL(new Blob([data as BlobPart], { type: mime }))
  const a = document.createElement('a'); a.href = url; a.download = `merged.${fmt}`; a.click()
  URL.revokeObjectURL(url)
}

export async function runEda(
  fileId: string,
  opts: { segment_col?: string; metric_cols?: string[]; log_transform?: 'auto' | 'on' | 'off' } = {},
): Promise<EdaReport> {
  const { data } = await client.post(`/ml/${fileId}/eda`, opts)
  return data
}
