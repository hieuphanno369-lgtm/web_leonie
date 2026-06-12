import client from './client'
import type { KpiEntry, KpiCategory } from '../types'

export interface KpiPayload {
  metric: string
  value: number
  date: string
  category: KpiCategory
  note?: string | null
}

export async function fetchKpi(params?: {
  metric?: string; category?: KpiCategory; from_date?: string; to_date?: string
}): Promise<KpiEntry[]> {
  const { data } = await client.get<KpiEntry[]>('/kpi', { params })
  return data
}

export async function fetchKpiMetrics(): Promise<string[]> {
  const { data } = await client.get<string[]>('/kpi/metrics')
  return data
}

export async function createKpi(body: KpiPayload): Promise<KpiEntry> {
  const { data } = await client.post<KpiEntry>('/kpi', body)
  return data
}

export async function deleteKpi(id: string): Promise<void> {
  await client.delete(`/kpi/${id}`)
}
