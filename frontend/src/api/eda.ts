import client from './client'
import type { EDARequest, EDAStatus } from '../types'

export interface EDAPayload {
  title: string
  requester: string
  dataset: string
  status?: EDAStatus
  priority?: 'low' | 'medium' | 'high'
  due_date?: string | null
  notes?: string | null
}

export async function fetchEDA(status?: EDAStatus): Promise<EDARequest[]> {
  const params = status ? { status } : {}
  const { data } = await client.get<EDARequest[]>('/eda', { params })
  return data
}

export async function createEDA(body: EDAPayload): Promise<EDARequest> {
  const { data } = await client.post<EDARequest>('/eda', body)
  return data
}

export async function updateEDA(id: string, body: Partial<EDAPayload>): Promise<EDARequest> {
  const { data } = await client.patch<EDARequest>(`/eda/${id}`, body)
  return data
}

export async function deleteEDA(id: string): Promise<void> {
  await client.delete(`/eda/${id}`)
}
