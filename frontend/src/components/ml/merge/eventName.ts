export interface ParsedEventName {
  /** The highlighted core — the store / event name. */
  event: string
  /** Normalised date token if present, else ''. */
  date: string
  /** Stripped boilerplate, joined by ' · ', shown as muted secondary text. */
  ctx: string
}

const EXT = /\.(xlsx|xlsm|xls|csv)$/i

// Boilerplate phrases common to these survey exports. Longest/most-specific first
// so e.g. "Thông tin khách hàng" is consumed before the shorter "Thông tin KH".
const CTX_TOKENS: { re: RegExp; label: string }[] = [
  { re: /Thông tin khách hàng/i, label: 'Thông tin khách hàng' },
  { re: /Thông tin KH/i,          label: 'Thông tin KH' },
  { re: /check[\s-]?in/i,         label: 'check-in' },
  { re: /chương trình/i,          label: 'chương trình' },
  { re: /Câu trả lời/i,           label: 'Câu trả lời' },
]

// Pull (and normalise) the first date-like token. Handles ranges, "T<m>.<y>",
// and dotted/underscored "d.m.y". Returns the remaining string with it removed.
function extractDate(s: string): { date: string; rest: string } {
  let m = s.match(/(\d{1,2})\s*[-–]\s*(\d{1,2})[._](\d{1,2})[._](\d{4})/)
  if (m) return { date: `${m[1]}–${m[2]}.${m[3]}.${m[4]}`, rest: s.replace(m[0], ' ') }
  m = s.match(/T(\d{1,2})[._](\d{4})/i)
  if (m) return { date: `T${m[1]}.${m[2]}`, rest: s.replace(m[0], ' ') }
  m = s.match(/(\d{1,2})[._](\d{1,2})[._](\d{4})/)
  if (m) return { date: `${m[1]}.${m[2]}.${m[3]}`, rest: s.replace(m[0], ' ') }
  return { date: '', rest: s }
}

/**
 * Extract the meaningful "event" from a survey-export filename, e.g.
 *   "Thông tin KH - Khai trương CH Jerry - T4.2026 (Câu trả lời).xlsx"
 *   → { event: "Khai trương CH Jerry", date: "T4.2026", ctx: "Thông tin KH · Câu trả lời" }
 *
 * Best-effort and lossless-safe: if nothing distinctive survives the strip,
 * it falls back to the bare filename so nothing is ever hidden entirely.
 */
export function parseEventName(filename: string): ParsedEventName {
  let s = filename.replace(EXT, '')
  const { date, rest } = extractDate(s)
  s = rest

  const ctx: string[] = []
  for (const t of CTX_TOKENS) {
    if (t.re.test(s)) { ctx.push(t.label); s = s.replace(t.re, ' ') }
  }

  s = s.replace(/\(\s*\d+\s*\)/g, ' ')   // drop "(1)" "(2)" disambiguators
  s = s.replace(/\(\s*\)/g, ' ')          // drop empty parens left by removals

  let event = s
    .replace(/(\d+)_(\d+)/g, '$1/$2')     // 8_3 → 8/3, 30_4 → 30/4
    .replace(/_/g, ' ')                    // remaining underscores → spaces
    .replace(/\s{2,}/g, ' ')
    .replace(/^[\s\-–:·]+/, '')
    .replace(/[\s\-–:·]+$/, '')
    .replace(/\s-\s/g, ' – ')              // " - " → " – "
    .trim()

  if (!event) event = filename.replace(EXT, '').trim()
  if (event) event = event.charAt(0).toUpperCase() + event.slice(1)

  return { event, date, ctx: ctx.join(' · ') }
}
