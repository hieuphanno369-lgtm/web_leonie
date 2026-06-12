import type { EdaReport } from '../../types'

export function edaToMarkdown(r: EdaReport): string {
  const lines: string[] = []
  lines.push(`# Auto-EDA — ${r.meta.filename}`)
  lines.push(`${r.meta.rows} dòng × ${r.meta.cols} cột`, '')
  lines.push('## Insights')
  r.insights.forEach((i, n) => {
    lines.push(`${n + 1}. **Finding:** ${i.finding}`)
    lines.push(`   - **So what:** ${i.so_what}`)
    lines.push(`   - **Action:** ${i.action}`)
  })
  lines.push('', '## Hồ sơ cột')
  lines.push('| Cột | Loại | Null % | Cardinality |')
  lines.push('| --- | --- | --- | --- |')
  r.profile.forEach(c =>
    lines.push(`| ${c.name} | ${c.role} | ${c.null_pct}% | ${c.cardinality} |`))
  return lines.join('\n')
}
