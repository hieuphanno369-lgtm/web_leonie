import client from './client'

export interface Snippet {
  id: string
  title: string
  category: string
  sql: string
  tags: string
  created: string
  updated: string
}

export interface SnippetIn {
  title: string
  category: string
  sql: string
  tags: string
}

export async function fetchSnippets(q = '', category = ''): Promise<Snippet[]> {
  const { data } = await client.get<Snippet[]>('/snippets', { params: { q, category } })
  return data
}

export async function createSnippet(body: SnippetIn): Promise<Snippet> {
  const { data } = await client.post<Snippet>('/snippets', body)
  return data
}

export async function updateSnippet(id: string, body: SnippetIn): Promise<Snippet> {
  const { data } = await client.put<Snippet>(`/snippets/${id}`, body)
  return data
}

export async function deleteSnippet(id: string): Promise<void> {
  await client.delete(`/snippets/${id}`)
}
