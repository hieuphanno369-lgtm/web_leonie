// ─── Navigation ─────────────────────────────────────────────────────────────

export type NavCategoryId = 'home' | 'work' | 'data' | 'analytics'

export interface NavItem {
  path: string
  label: string
  iconName: string      // Lucide icon name, e.g. 'LayoutDashboard'
  color: string         // accent hex for this category
}

export interface NavCategory {
  id: NavCategoryId
  label: string
  color: string
  items: NavItem[]
}

// ─── API responses ───────────────────────────────────────────────────────────

export interface HealthResponse {
  status: 'ok'
  version: string
}

// ─── Domain models (populated in SP2+) ──────────────────────────────────────

export type TaskStatus   = 'todo' | 'in_progress' | 'done'
export type TaskPriority = 'low' | 'medium' | 'high'
export type TaskType     = 'task' | 'eda'

export interface Task {
  id: string
  title: string
  type: TaskType
  status: TaskStatus
  priority: TaskPriority
  due_date: string | null
  recurring: 'daily' | 'weekly' | null
  notes: string | null
  requester: string | null
  dataset: string | null
  created: string
  updated: string
}

export interface Snippet {
  id: string
  filename: string
  category: string
  sql: string
  source: 'file' | 'user'
  created: string
  updated: string
}

// ─── EDA Tracker ────────────────────────────────────────────────────────────

export type EDAStatus   = 'todo' | 'in_progress' | 'done'
export type EDAPriority = 'low' | 'medium' | 'high'

export interface EDARequest {
  id: string
  title: string
  requester: string
  dataset: string
  priority: EDAPriority
  status: EDAStatus
  due_date: string | null
  notes: string | null
  created: string
  updated: string
}

// ─── WIP Builder ────────────────────────────────────────────────────────────

export interface WIPItem {
  id: string
  task_id: string
  task_title: string
  progress: number
  created: string
  updated: string
}

export interface WIPLog {
  id: string
  wip_id: string
  date: string
  note: string
  created: string
}

// ─── Discord Notify ──────────────────────────────────────────────────────────

export interface DiscordSettings {
  webhook_url: string | null
  rule_overdue: boolean
  rule_done: boolean
  rule_summary: boolean
  last_checked: string | null
}

// ─── KPI Tracker ─────────────────────────────────────────────────────────────

export type KpiCategory = 'da_output' | 'business'

export interface KpiEntry {
  id: string
  metric: string
  value: number
  date: string
  category: KpiCategory
  note: string | null
  created: string
}

// ─── Performance ─────────────────────────────────────────────────────────────

export interface DayStatus {
  date: string
  status: 'hit' | 'partial' | 'miss'
}

export interface StreakCondition {
  type: 'tasks_done' | 'eda_done' | 'kpi_logged' | 'wip_updated'
  op: 'gte'
  value: number
}

export interface StreakRule {
  conditions: StreakCondition[]
  logic: 'AND' | 'OR'
}

export interface PerformanceSummary {
  streak: number
  tasks_done: number
  eda_done: number
  kpi_logs: number
  wip_avg_progress: number
  calendar: DayStatus[]
}

// ─── ML Studio ───────────────────────────────────────────────────────────────

export interface ColumnInfo {
  name: string
  dtype: string
}

export interface DatasetInfo {
  file_id: string
  filename: string
  rows: number
  cols: number
  columns: ColumnInfo[]
}

export interface QueryResult {
  columns: string[]
  rows: unknown[][]
  duration_ms: number
}

export interface StatsResult {
  [key: string]: number | string | undefined
  code?: string
}

export interface ForecastPoint {
  date: string
  value: number
  /** 95% CI bound, or null when the model can't estimate it (e.g. SARIMAX on a marginal series). */
  lower: number | null
  upper: number | null
}

export interface HistoryPoint {
  date: string
  value: number
  is_anomaly: boolean
  z_score: number
}

export interface ForecastResult {
  method: string
  slope: number
  intercept: number
  forecast: ForecastPoint[]
  history?: HistoryPoint[]
  aic?: number
  r2?: number
  lags_used?: number
  trained_on?: number
  alpha?: number
  beta?: number
  gamma?: number
  code?: string
  suitable?: boolean
  reasons?: string[]
  recommended_method?: string | null
  grain?: string
}

export interface ForecastCompareRow {
  method: string
  label: string
  mape: number | null
  rmse: number | null
  aic: number | null
  status: 'ok' | 'error'
  error?: string
}

export interface ForecastCompareResult {
  results: ForecastCompareRow[]
  best: string
}

export interface ForecastInterpretResult {
  summary: string
  trend: string
  actions: string
}

export interface CorrelationMatrix {
  columns: string[]
  matrix: (number | null)[][]
  excluded_columns?: { name: string; reason: string }[]
  code?: string
}

export interface TimeseriesResult {
  grain: 'day' | 'week' | 'month' | 'quarter' | 'year'
  agg: string
  date_col: string
  value_col: string
  series: { labels: string[]; values: (number | null)[] }
  comparisons: {
    yoy?: { values: (number | null)[]; delta_pct: (number | null)[] }
    pop?: { values: (number | null)[]; delta_pct: (number | null)[] }
    rolling?: { window: number; values: (number | null)[] }
    cumulative?: { reset: string; values: (number | null)[] }
    index100?: { values: (number | null)[] }
    share?: { values: (number | null)[] }
  }
  meta: { rows_used: number; periods: number; span_days: number; suggested_grain: string }
  code?: string
}

export interface ProfileColumn {
  name: string
  dtype: string
  role: 'date' | 'metric' | 'dimension' | 'id' | 'flag'
  cardinality: number
  null_pct: number
  is_constant: boolean
  samples: string[]
  min?: number
  max?: number
}

export interface DrilldownResult {
  grain: 'year' | 'month' | 'day'
  labels: string[]
  values: (number | null)[]
  value_col: string
  agg: string
  code?: string
}

export interface ProfileResult {
  columns: ProfileColumn[]
  rows: number
}

// ─── ML Merge ─────────────────────────────────────────────────────────────────

export type SemanticType = 'phone' | 'email' | 'date' | 'number' | 'category' | 'text'

export interface MergeFileSchema {
  filename: string
  fields: string[]
}

export interface ColumnProfile {
  file: string
  name: string
  norm: string
  inferred_type: SemanticType
  confidence: number
  samples: string[]
  non_null: number
  distinct: number
  fill_rate: number
}

export interface FieldGroupSuggestion {
  canonical: string
  members: string[]
  inferred_type: SemanticType
  confidence: number
  reason: 'name' | 'type' | 'name+type'
}

export interface MergeStageResult {
  session_id: string
  files: MergeFileSchema[]
  common_fields: string[]
  all_fields: string[]
  profiles: ColumnProfile[]
  suggestions: FieldGroupSuggestion[]
}

export interface MergeOptions {
  dedup_key: string | null
  drop_invalid_key: boolean
  trim: boolean
  semantic_types: Record<string, SemanticType>
  field_groups: Record<string, string[]>
  required_fields: string[]
  coalesce: boolean
}

export interface MergeSummary {
  total_raw: number
  valid_format: number
  null_or_wrong: number
  distinct: number
  dup_removed_clean: number
  dup_removed_raw: number
  complete: number
  incomplete: number
  rejected: number
  per_field_fill_rate: Record<string, number>
  per_file_contribution: Record<string, number>
}

export interface MergeRunResult {
  summary: MergeSummary
  dataset?: DatasetInfo
  preview?: Record<string, string | null>[]
  rejected_url?: string
  code?: string                 // Show Code: full Combine pipeline (dry-run & real)
}

// ─── ML Auto-EDA ──────────────────────────────────────────────────────────────

export interface EdaInsight {
  finding: string
  so_what: string
  action: string
  severity: 'low' | 'medium' | 'high'
}

export interface EdaDistribution {
  column: string
  bins: { x0: number; x1: number; count: number }[]
  skew: number
  log_applied: boolean
  mean: number
  median: number
  std: number
  min: number
  max: number
}

export interface EdaSegmentRow {
  segment: string
  count: number
  [metricAgg: string]: number | string
}

export interface EdaScatterPoint { x: number; y: number; group: string }

export interface EdaReport {
  meta: {
    rows: number; cols: number; filename: string
    segment_col: string | null; metric_cols: string[]
  }
  profile: ProfileColumn[]
  correlation: CorrelationMatrix
  distributions: EdaDistribution[]
  segments: {
    table: EdaSegmentRow[]
    scatter: { x_col: string | null; y_col: string | null; points: EdaScatterPoint[] }
  }
  insights: EdaInsight[]
  insights_source: 'ai' | 'rule'
}

// ─── ML Data Quality ──────────────────────────────────────────────────────────

export interface QualityIssue {
  type: 'null' | 'outlier' | 'duplicate' | 'constant' | 'dtype'
  column: string | null
  detail: string
}

export interface QualityResult {
  file_id: string
  rows: number
  cols: number
  issues: QualityIssue[]
  issue_count: number
}

// ─── ML Z-Score ───────────────────────────────────────────────────────────────

export interface ZScoreRow {
  idx:     number
  value:   number
  z_score: number
}

export interface ZScoreData {
  mean:           number
  std:            number
  n:              number
  rows:           ZScoreRow[]
  histogram_bins: Array<{ x0: number; x1: number; count: number }>
}

// ─── ML Box Plot ──────────────────────────────────────────────────────────────

export interface BoxPlotGroup {
  name:              string
  n:                 number
  min:               number
  q1:                number
  median:            number
  q3:                number
  max:               number
  iqr:               number
  lower_fence:       number
  upper_fence:       number
  outliers:          Array<{ idx: number; value: number }>
  total_outliers:    number
  outliers_truncated: boolean
}

export interface BoxPlotData {
  groups:        BoxPlotGroup[]
  total_n:       number
  total_groups:  number
  truncated:     boolean
}

// ─── Action Plan ─────────────────────────────────────────────────────────────

export type APCategory = 'rfm' | 'cohort' | 'statistical' | 'etl' | 'dashboard' | 'other'
export type APStatus   = 'draft' | 'proposed' | 'approved' | 'in_progress' | 'done'
export type APPriority = 'low' | 'medium' | 'high'
export type APApproval = 'pending' | 'approved' | 'rejected'

export interface ChecklistItem { done: boolean; text: string }
export interface TimelineItem  { week: string; tasks: string }
export interface APInput       { sources: string[]; tables: string[]; notes: string }
export interface APOutput      { deliverable: string; format: string }
export interface APRef         { company: string; method: string; summary: string; verified: boolean }

export interface ActionPlan {
  id: string
  title: string
  category: APCategory
  status: APStatus
  priority: APPriority
  problem: string | null
  pic_main: string | null
  pic_support: string | null
  due_date: string | null
  manager_notes: string | null
  approval: APApproval
  ai_timeline: string | null
  ai_checklist: string | null
  ai_input: string | null
  ai_output: string | null
  ai_value: string | null
  ai_impact: string | null
  ai_refs: string | null
  ai_suggestions: string | null
  created: string
  updated: string
}

// ─── Quick Notes ──────────────────────────────────────────────────────────────

export interface QuickNote {
  id: string
  title: string | null
  content: string
  date: string          // YYYY-MM-DD
  category: string | null
  task_id: string | null
  eda_id: string | null
  created: string
  updated: string
}

// ─── Automation ───────────────────────────────────────────────────────────────

export type RestAuthType = 'none' | 'api_key' | 'basic' | 'bearer'

export interface RestAuth {
  type: RestAuthType
  header_name?: string | null   // api_key: header to set (e.g. "X-API-Key")
  value_ref?: string | null     // api_key/bearer: env-var NAME holding the secret
  user_ref?: string | null      // basic: env-var name for username
  pass_ref?: string | null      // basic: env-var name for password
}

export interface Pagination {
  param: string                 // query param name, e.g. "page"
  start: number                 // first page number
}

export interface RestSource {
  source_type: 'rest'
  url: string
  method: 'GET'
  headers: Record<string, string>   // values may contain ${VAR}
  params: Record<string, string>
  auth: RestAuth
  records_path: string              // dotted path to the array, e.g. "data.items" ("" = root)
  pagination: Pagination | null
  timeout_seconds: number
  max_retries: number
}

export interface SalesforceSource {
  source_type: 'salesforce'
  soql: string
  object_name: string
  use_bulk: boolean
  user_ref: string      // env var name for username (default: SF_User)
  pass_ref: string      // env var name for password (default: SF_Password)
  token_ref: string     // env var name for security token ("" = no token)
  instance_url: string
}

export type AnySource = RestSource | SalesforceSource
export type SourceType = 'rest' | 'salesforce'

export type ExportFormat = 'duckdb' | 'parquet' | 'csv' | 'xlsx'

export interface ExportSpec {
  formats: ExportFormat[]
  dest_dir: string
  duckdb_mode: 'overwrite' | 'append'
  xlsx_row_guard: number
}

export interface EmailSpec {
  enabled: boolean
  recipients: string[]
  attach_max_bytes: number
}

export interface NotifySpec {
  discord_enabled: boolean
  email: EmailSpec
}

export interface JobConfig {
  name: string
  source: AnySource
  shape_sql: string             // DuckDB SQL over `raw`; "" = passthrough
  export: ExportSpec
  notify: NotifySpec
}

export type RunStatusValue = 'ok' | 'warning' | 'error' | 'running'

export interface RunResult {
  status: RunStatusValue
  rows: number
  duration_seconds: number
  output_files: string[]
  error: string | null
}

export interface AutomationJob {
  id: string
  config: JobConfig
  last_status: string | null
  last_run_at: string | null
  last_rows: number | null
  last_error: string | null
  created: string
  updated: string
}

export interface PreviewResult {     // POST /jobs/{id}/preview
  columns: string[]
  rows: unknown[][]
}

export interface JobCode {           // GET /jobs/{id}/code
  python: string
  sql: string
}
