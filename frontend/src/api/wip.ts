import client from './client'
import type { WIPItem, WIPLog } from '../types'

export async function fetchWIPs(): Promise<WIPItem[]> {
  const { data } = await client.get<WIPItem[]>('/wip')
  return data
}

export async function createWIP(task_id: string, progress = 0): Promise<WIPItem> {
  const { data } = await client.post<WIPItem>('/wip', { task_id, progress })
  return data
}

export async function updateWIPProgress(id: string, progress: number): Promise<WIPItem> {
  const { data } = await client.patch<WIPItem>(`/wip/${id}`, { progress })
  return data
}

export async function deleteWIP(id: string): Promise<void> {
  await client.delete(`/wip/${id}`)
}

export async function fetchLogs(wip_id: string): Promise<WIPLog[]> {
  const { data } = await client.get<WIPLog[]>(`/wip/${wip_id}/logs`)
  return data
}

export async function addLog(wip_id: string, date: string, note: string): Promise<WIPLog> {
  const { data } = await client.post<WIPLog>(`/wip/${wip_id}/logs`, { date, note })
  return data
}

export async function deleteLog(wip_id: string, log_id: string): Promise<void> {
  await client.delete(`/wip/${wip_id}/logs/${log_id}`)
}
