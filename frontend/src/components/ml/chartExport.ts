/** Quote a CSV cell per RFC 4180 (wrap in quotes if it contains comma/quote/newline). */
function csvCell(v: unknown): string {
  const s = v == null ? '' : String(v)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

export function toCsv(columns: string[], rows: unknown[][]): string {
  const head = columns.map(csvCell).join(',')
  const body = rows.map(r => r.map(csvCell).join(',')).join('\n')
  return body ? `${head}\n${body}` : head
}

/** Copy rows as CSV to the clipboard. Returns true on success. */
export async function copyRowsAsCsv(columns: string[], rows: unknown[][]): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(toCsv(columns, rows))
    return true
  } catch {
    return false
  }
}

/** Trigger a .csv file download. */
export function downloadCsv(columns: string[], rows: unknown[][], filename = 'export.csv'): void {
  const blob = new Blob([toCsv(columns, rows)], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

/**
 * Best-effort PNG export of an inline <svg> (e.g. a recharts chart).
 * Serializes the SVG, paints it onto a canvas, and downloads a PNG.
 * Resolves false on any failure (tainted canvas, missing svg) — caller shows a toast.
 */
export function downloadSvgAsPng(svg: SVGSVGElement | null, filename = 'chart.png'): Promise<boolean> {
  return new Promise((resolve) => {
    if (!svg) { resolve(false); return }
    try {
      const rect = svg.getBoundingClientRect()
      const w = Math.max(1, Math.round(rect.width || svg.clientWidth || 800))
      const h = Math.max(1, Math.round(rect.height || svg.clientHeight || 400))
      const clone = svg.cloneNode(true) as SVGSVGElement
      clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
      clone.setAttribute('width', String(w))
      clone.setAttribute('height', String(h))
      const xml = new XMLSerializer().serializeToString(clone)
      const svg64 = 'data:image/svg+xml;base64,' + window.btoa(unescape(encodeURIComponent(xml)))
      const img = new Image()
      img.onload = () => {
        try {
          const scale = window.devicePixelRatio || 1
          const canvas = document.createElement('canvas')
          canvas.width = w * scale; canvas.height = h * scale
          const ctx = canvas.getContext('2d')
          if (!ctx) { resolve(false); return }
          ctx.scale(scale, scale)
          ctx.fillStyle = '#0d1117'           // match app background (avoid transparent black)
          ctx.fillRect(0, 0, w, h)
          ctx.drawImage(img, 0, 0, w, h)
          const png = canvas.toDataURL('image/png')
          const a = document.createElement('a')
          a.href = png; a.download = filename; a.click()
          resolve(true)
        } catch { resolve(false) }
      }
      img.onerror = () => resolve(false)
      img.src = svg64
    } catch {
      resolve(false)
    }
  })
}
