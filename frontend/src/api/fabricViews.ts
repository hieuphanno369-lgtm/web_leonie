import client from './client'

export interface FabricView {
  id: string
  name: string
  schema_name: string
  category: string
  description: string
  sql_def: string
  tags: string
  created: string
  updated: string
}

export interface FabricViewIn {
  name: string
  schema_name: string
  category: string
  description: string
  sql_def: string
  tags: string
}

export async function fetchViews(q = '', category = ''): Promise<FabricView[]> {
  const { data } = await client.get<FabricView[]>('/fabric-views', { params: { q, category } })
  return data
}

export async function createView(body: FabricViewIn): Promise<FabricView> {
  const { data } = await client.post<FabricView>('/fabric-views', body)
  return data
}

export async function updateView(id: string, body: FabricViewIn): Promise<FabricView> {
  const { data } = await client.put<FabricView>(`/fabric-views/${id}`, body)
  return data
}

export async function deleteView(id: string): Promise<void> {
  await client.delete(`/fabric-views/${id}`)
}
