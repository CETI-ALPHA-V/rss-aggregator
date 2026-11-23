export type TypeFilter = 'all' | 'blog' | 'releases' | 'video'

export type Filters = {
  categories: string[]
  platforms: string[]
  type: TypeFilter
  days: number | null
  q: string
}

export const DEFAULT_DAYS = 30

export const DAY_OPTIONS: { label: string; short: string; value: number | null }[] = [
  { label: 'Today', short: '1d', value: 1 },
  { label: '7 days', short: '7d', value: 7 },
  { label: '30 days', short: '30d', value: 30 },
  { label: '60 days', short: '60d', value: 60 },
  { label: 'All time', short: 'All', value: null },
]

export const TYPE_OPTIONS: { label: string; value: TypeFilter }[] = [
  { label: 'All', value: 'all' },
  { label: 'Blog', value: 'blog' },
  { label: 'Releases', value: 'releases' },
  { label: 'Videos', value: 'video' },
]

export function readFilters(sp: URLSearchParams): Filters {
  const rawDays = sp.get('days')
  const parsedDays = rawDays && rawDays !== 'all' ? Number(rawDays) : NaN
  const rawType = sp.get('type')
  return {
    categories: sp.getAll('category'),
    platforms: sp.getAll('platform'),
    type: rawType === 'blog' || rawType === 'releases' || rawType === 'video' ? rawType : 'all',
    days: rawDays === 'all' ? null : Number.isFinite(parsedDays) && parsedDays > 0 ? parsedDays : DEFAULT_DAYS,
    q: sp.get('q') ?? '',
  }
}

/** Serialises filters into URL params, keeping any unrelated params from `base`. */
export function writeFilters(f: Filters, base: URLSearchParams): URLSearchParams {
  const sp = new URLSearchParams(base)
  for (const key of ['category', 'platform', 'type', 'days', 'q']) sp.delete(key)
  f.categories.forEach((c) => sp.append('category', c))
  f.platforms.forEach((p) => sp.append('platform', p))
  if (f.type !== 'all') sp.set('type', f.type)
  if (f.days === null) sp.set('days', 'all')
  else if (f.days !== DEFAULT_DAYS) sp.set('days', String(f.days))
  if (f.q.trim()) sp.set('q', f.q.trim())
  return sp
}

export function toApiParams(f: Filters): URLSearchParams {
  const sp = new URLSearchParams()
  f.categories.forEach((c) => sp.append('category', c))
  f.platforms.forEach((p) => sp.append('platform', p))
  if (f.type !== 'all') sp.set('type', f.type)
  if (f.days !== null) sp.set('days', String(f.days))
  if (f.q.trim()) sp.set('q', f.q.trim())
  return sp
}

export function hasActiveFilters(f: Filters): boolean {
  return f.categories.length > 0 || f.platforms.length > 0 || f.type !== 'all' || f.q.trim() !== ''
}

export function toggle<T>(list: T[], item: T): T[] {
  return list.includes(item) ? list.filter((x) => x !== item) : [...list, item]
}
