const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto', style: 'short' })

/** "2 min. ago", "yesterday", … */
export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return '—'
  const seconds = Math.round((new Date(iso).getTime() - Date.now()) / 1000)
  const abs = Math.abs(seconds)
  if (abs < 45) return 'just now'
  if (abs < 3600) return rtf.format(Math.round(seconds / 60), 'minute')
  if (abs < 86400) return rtf.format(Math.round(seconds / 3600), 'hour')
  return rtf.format(Math.round(seconds / 86400), 'day')
}

export function clockTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export function initials(name: string | null | undefined, fallback = '?'): string {
  if (!name) return fallback
  const parts = name.trim().split(/\s+/)
  return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase() || fallback
}

export function contactLabel(c: { name: string | null; email: string | null }): string {
  return c.name || c.email || 'Unknown contact'
}
