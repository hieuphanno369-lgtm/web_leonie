import type { ProfileResult } from '../../types'

export type RecipeKind = 'timeseries' | 'correlation' | 'bar' | 'scatter' | 'clustered'
export type RecipeIcon = 'TrendingUp' | 'Link2' | 'BarChart3' | 'ScatterChart' | 'Grid2x2'

export interface Recipe {
  title: string
  kind: RecipeKind
  iconName: RecipeIcon
  x?: string
  y?: string
  ys?: string[]
}

/**
 * Build a (possibly large) pool of chart suggestions from the dataset profile,
 * guarded so client-side recipes only reference columns present in the current
 * SQL result. Pure & deterministic — unit-testable without React.
 *
 * Example: profile with date "Order Date", metrics ["Sales","Profit","Qty"],
 * dims ["Region","Segment"], flags ["Returned"] yields, in order:
 *   timeseries(Sales by Order Date), timeseries(Profit by Order Date),
 *   correlation(3 metrics), clustered(Region × [Sales,Profit,Qty]),
 *   bar(Sales by Region), bar(Sales by Segment), bar(Sales by Returned [flag]),
 *   scatter(Sales vs Profit), scatter(Sales vs Qty), ...
 */
export function buildRecipePool(profile: ProfileResult | null, resultColumns: string[]): Recipe[] {
  if (!profile) return []
  const inResult = (name: string) => resultColumns.includes(name)
  const dates   = profile.columns.filter(c => c.role === 'date')
  const metrics = profile.columns.filter(c => c.role === 'metric')
  const dims    = profile.columns.filter(c => c.role === 'dimension')
  const flags   = profile.columns.filter(c => c.role === 'flag')
  const out: Recipe[] = []

  // Date × metric → server-side time series (each metric = a different angle)
  for (const d of dates) {
    for (const m of metrics.slice(0, 4)) {
      out.push({ title: `${m.name} theo thời gian (${d.name})`, kind: 'timeseries', iconName: 'TrendingUp', x: d.name, y: m.name })
    }
  }
  // ≥2 metrics → correlation
  if (metrics.length >= 2) {
    out.push({ title: `Tương quan ${metrics.length} cột số`, kind: 'correlation', iconName: 'Link2' })
  }
  // ≥2 metrics present in result → clustered measures
  const metricsInResult = metrics.filter(m => inResult(m.name))
  if (dims[0] && metricsInResult.length >= 2 && inResult(dims[0].name)) {
    out.push({
      title: `${dims[0].name}: ${metricsInResult.slice(0, 3).map(m => m.name).join(' · ')}`,
      kind: 'clustered', iconName: 'Grid2x2', x: dims[0].name, ys: metricsInResult.slice(0, 3).map(m => m.name),
    })
  }
  // Dimension × metric → bar (guarded to result columns)
  for (const dim of dims) {
    for (const m of metrics.slice(0, 2)) {
      if (inResult(dim.name) && inResult(m.name)) {
        out.push({ title: `${m.name} theo ${dim.name}`, kind: 'bar', iconName: 'BarChart3', x: dim.name, y: m.name })
      }
    }
  }
  // Flag × metric → bar (e.g. has_campaign)
  for (const f of flags) {
    if (metrics[0] && inResult(f.name) && inResult(metrics[0].name)) {
      out.push({ title: `${metrics[0].name} theo ${f.name}`, kind: 'bar', iconName: 'BarChart3', x: f.name, y: metrics[0].name })
    }
  }
  // Metric × metric → scatter (guarded)
  for (let i = 0; i < metrics.length; i++) {
    for (let j = i + 1; j < metrics.length; j++) {
      if (inResult(metrics[i].name) && inResult(metrics[j].name)) {
        out.push({ title: `${metrics[i].name} vs ${metrics[j].name}`, kind: 'scatter', iconName: 'ScatterChart', x: metrics[i].name, y: metrics[j].name })
      }
    }
  }
  return out
}
