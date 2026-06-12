import client from './client'
import type { PerformanceSummary, StreakRule } from '../types'

export async function fetchPerformanceSummary(): Promise<PerformanceSummary> {
  const { data } = await client.get<PerformanceSummary>('/performance/summary')
  return data
}

export async function fetchStreakRule(): Promise<{ streak_rule: StreakRule }> {
  const { data } = await client.get<{ streak_rule: StreakRule }>('/performance/settings')
  return data
}

export async function saveStreakRule(rule: StreakRule): Promise<{ streak_rule: StreakRule }> {
  const { data } = await client.post<{ streak_rule: StreakRule }>('/performance/settings', { streak_rule: rule })
  return data
}
