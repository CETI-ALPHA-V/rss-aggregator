const DAY_MS = 86_400_000

export function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

function startOfDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
}

export function dayKey(d: Date | null): string {
  return d ? new Date(startOfDay(d)).toISOString() : 'undated'
}

export function dayLabel(d: Date | null, now = new Date()): string {
  if (!d) return 'Undated'
  const diff = Math.round((startOfDay(now) - startOfDay(d)) / DAY_MS)
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Yesterday'
  if (diff === -1) return 'Tomorrow'
  return d.toLocaleDateString(undefined, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    ...(d.getFullYear() !== now.getFullYear() ? { year: 'numeric' } : {}),
  })
}

export function shortDate(d: Date, now = new Date()): string {
  return d.toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    ...(d.getFullYear() !== now.getFullYear() ? { year: 'numeric' } : {}),
  })
}

export function relativeTime(d: Date | null, now = new Date()): string {
  if (!d) return ''
  const secs = (now.getTime() - d.getTime()) / 1000
  if (secs < 0) return shortDate(d, now)
  if (secs < 60) return 'just now'
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`
  if (secs < 86_400) return `${Math.floor(secs / 3600)}h ago`
  if (secs < 7 * 86_400) return `${Math.floor(secs / 86_400)}d ago`
  return shortDate(d, now)
}

export function fullDate(d: Date | null): string {
  return d ? d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : ''
}

export function domainOf(url: string): string {
  try {
    const host = new URL(url).hostname
    return host.startsWith('www.') ? host.slice(4) : host
  } catch {
    return ''
  }
}

/** The video id for youtube.com/watch?v=…, youtube.com/shorts/… and youtu.be/… links. */
export function youtubeId(url: string): string | null {
  try {
    const u = new URL(url)
    if (u.hostname === 'youtu.be') return u.pathname.slice(1) || null
    if (!u.hostname.endsWith('youtube.com')) return null
    if (u.pathname.startsWith('/shorts/')) return u.pathname.split('/')[2] || null
    return u.searchParams.get('v')
  } catch {
    return null
  }
}

/** White or near-black text, whichever reads better on `hex`. */
export function readableText(hex: string): string {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex)
  if (!m) return '#ffffff'
  const n = parseInt(m[1], 16)
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => {
    const c = v / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  })
  const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
  return luminance > 0.45 ? '#18181b' : '#ffffff'
}

const FALLBACK_PALETTE = ['#6366f1', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#14b8a6', '#ec4899']

/** Known brand colour if we have one, otherwise a stable colour derived from the name. */
export function colorFor(name: string, known: Record<string, string> = {}): string {
  if (known[name]) return known[name]
  let h = 0
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) >>> 0
  return FALLBACK_PALETTE[h % FALLBACK_PALETTE.length]
}

export function plural(n: number, word: string, pluralWord = `${word}s`): string {
  return `${n.toLocaleString()} ${n === 1 ? word : pluralWord}`
}
