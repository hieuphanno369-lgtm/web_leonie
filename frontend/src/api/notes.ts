import client from './client'
import type { QuickNote } from '../types'

export interface NoteParams {
  date_from?: string
  date_to?: string
  category?: string
  task_id?: string
  eda_id?: string
}

export interface NotePayload {
  title?: string | null
  content: string
  date: string
  category?: string | null
  task_id?: string | null
  eda_id?: string | null
}

export async function fetchNotes(params?: NoteParams): Promise<QuickNote[]> {
  const filtered = params
    ? Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v != null))
    : {}
  const { data } = await client.get<QuickNote[]>('/notes', { params: filtered })
  return data
}

export async function createNote(body: NotePayload): Promise<QuickNote> {
  const { data } = await client.post<QuickNote>('/notes', body)
  return data
}

export async function updateNote(id: string, body: Partial<NotePayload>): Promise<QuickNote> {
  const { data } = await client.patch<QuickNote>(`/notes/${id}`, body)
  return data
}

export async function deleteNote(id: string): Promise<void> {
  await client.delete(`/notes/${id}`)
}
