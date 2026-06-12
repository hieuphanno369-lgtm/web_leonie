import client from './client'
import type { ActionPlan, APStatus } from '../types'

export interface APPayload {
  title: string
  category?: string
  status?: APStatus
  priority?: 'low' | 'medium' | 'high'
  problem?: string | null
  pic_main?: string | null
  pic_support?: string | null
  due_date?: string | null
  manager_notes?: string | null
  approval?: string
}

export async function fetchPlans(status?: APStatus): Promise<ActionPlan[]> {
  const params = status ? { status } : {}
  const { data } = await client.get<ActionPlan[]>('/action-plans', { params })
  return data
}

export async function createPlan(body: APPayload): Promise<ActionPlan> {
  const { data } = await client.post<ActionPlan>('/action-plans', body)
  return data
}

export async function updatePlan(id: string, body: Partial<APPayload> & { ai_checklist?: string }): Promise<ActionPlan> {
  const { data } = await client.patch<ActionPlan>(`/action-plans/${id}`, body)
  return data
}

export async function deletePlan(id: string): Promise<void> {
  await client.delete(`/action-plans/${id}`)
}

export async function generatePlan(id: string): Promise<ActionPlan> {
  const { data } = await client.post<ActionPlan>(`/action-plans/${id}/generate`)
  return data
}

export async function refinePlan(id: string, condition: string): Promise<ActionPlan> {
  const { data } = await client.post<ActionPlan>(`/action-plans/${id}/refine`, { condition })
  return data
}
