import client from './client'
import type { Task, TaskStatus, TaskType } from '../types'

export interface TaskPayload {
  title: string
  type?: TaskType
  status?: TaskStatus
  priority?: 'low' | 'medium' | 'high'
  due_date?: string | null
  recurring?: 'daily' | 'weekly' | null
  notes?: string | null
  requester?: string | null
  dataset?: string | null
}

export async function fetchTasks(status?: TaskStatus, type?: TaskType): Promise<Task[]> {
  const params: Record<string, string> = {}
  if (status) params.status = status
  if (type)   params.type   = type
  const { data } = await client.get<Task[]>('/tasks', { params })
  return data
}

export async function createTask(body: TaskPayload): Promise<Task> {
  const { data } = await client.post<Task>('/tasks', body)
  return data
}

export async function updateTask(id: string, body: Partial<TaskPayload>): Promise<Task> {
  const { data } = await client.patch<Task>(`/tasks/${id}`, body)
  return data
}

export async function deleteTask(id: string): Promise<void> {
  await client.delete(`/tasks/${id}`)
}
