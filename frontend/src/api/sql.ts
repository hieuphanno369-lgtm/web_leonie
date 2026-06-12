import client from './client'

export interface ColumnInfo {
  name:  string
  dtype: string
}

export interface TableInfo {
  file_id:    string
  table_name: string
  filename:   string
  rows:       number
  cols:       number
  columns:    ColumnInfo[]
  source:     'vina_brew' | 'user'
}

export interface SqlResult {
  columns:     string[]
  rows:        unknown[][]
  duration_ms: number
  tables:      string[]
}

export interface ExerciseCheckResult {
  passed:           boolean
  actual_columns:   string[]
  expected_columns: string[]
  error?:           string
}

export async function fetchTables(): Promise<TableInfo[]> {
  const { data } = await client.get<TableInfo[]>('/sql/tables')
  return data
}

export async function runSql(sql: string): Promise<SqlResult> {
  const { data } = await client.post<SqlResult>('/sql/query', { sql })
  return data
}

export async function deleteDataset(fileId: string): Promise<void> {
  await client.delete(`/sql/dataset/${fileId}`)
}

export async function seedVinaBrew(): Promise<{ seeded: string[]; total: number }> {
  const { data } = await client.post('/sql/seed-vina-brew')
  return data
}

export async function checkExercise(params: {
  exercise_id:      string
  sql:              string
  expected_columns: string[]
}): Promise<ExerciseCheckResult> {
  const { data } = await client.post<ExerciseCheckResult>('/sql/exercises/check', params)
  return data
}
