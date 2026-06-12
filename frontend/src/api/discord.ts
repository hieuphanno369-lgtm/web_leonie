import client from './client'
import type { DiscordSettings } from '../types'

export async function fetchDiscordSettings(): Promise<DiscordSettings> {
  const { data } = await client.get<DiscordSettings>('/discord/settings')
  return data
}

export async function saveDiscordSettings(body: Partial<DiscordSettings>): Promise<DiscordSettings> {
  const { data } = await client.post<DiscordSettings>('/discord/settings', body)
  return data
}

export async function sendDiscordMessage(message: string): Promise<void> {
  await client.post('/discord/send', { message })
}

export async function checkDiscordRules(): Promise<{ sent: number }> {
  const { data } = await client.post<{ sent: number }>('/discord/check')
  return data
}
