import client from './client'
import type { AutomationJob, JobConfig, PreviewResult, JobCode } from '../types'

export async function listJobs(): Promise<AutomationJob[]> {
  const { data } = await client.get<AutomationJob[]>('/automation/jobs')
  return data
}

export async function getJob(id: string): Promise<AutomationJob> {
  const { data } = await client.get<AutomationJob>(`/automation/jobs/${id}`)
  return data
}

export async function createJob(config: JobConfig): Promise<AutomationJob> {
  const { data } = await client.post<AutomationJob>('/automation/jobs', config)
  return data
}

export async function updateJob(id: string, config: JobConfig): Promise<AutomationJob> {
  const { data } = await client.put<AutomationJob>(`/automation/jobs/${id}`, config)
  return data
}

export async function deleteJob(id: string): Promise<void> {
  await client.delete(`/automation/jobs/${id}`)
}

export async function previewJob(id: string, n_rows = 100): Promise<PreviewResult> {
  const { data } = await client.post<PreviewResult>(
    `/automation/jobs/${id}/preview`,
    { n_rows },
    { timeout: 120_000 },          // a preview hits the live REST API; allow more time
  )
  return data
}

export async function runJob(id: string): Promise<{ status: string }> {
  const { data } = await client.post<{ status: string }>(`/automation/jobs/${id}/run`, {})
  return data
}

export async function getJobCode(id: string): Promise<JobCode> {
  const { data } = await client.get<JobCode>(`/automation/jobs/${id}/code`)
  return data
}

export interface VerifyPathResult {
  ok:          boolean
  exists:      boolean
  will_create: boolean
  writable:    boolean
  message:     string
}

export async function verifyPath(path: string): Promise<VerifyPathResult> {
  const { data } = await client.post<VerifyPathResult>('/automation/verify-path', { path })
  return data
}
