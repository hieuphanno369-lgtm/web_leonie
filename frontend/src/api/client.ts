import axios from 'axios'
import type { HealthResponse } from '../types'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api',
  headers: { 'Content-Type': 'application/json' },
  // 60s: first load of a large dataset still parses the source before the
  // parquet cache exists; the old 10s ceiling aborted those into "Query failed".
  timeout: 60_000,
})

export default client

// ─── Health ─────────────────────────────────────────────────────────────────

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await client.get<HealthResponse>('/health')
  return data
}
