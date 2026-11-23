import { useEffect, useState } from 'react'

export type ContentType = 'blog' | 'releases' | 'video'

export type Article = {
  feed_id: string
  link: string
  title: string
  summary: string | null
  published: string | null
  platform: string
  category: string
  type: ContentType
}

export type Platform = { name: string; categories: string[]; color: string; articles: number }

export type Meta = {
  categories: string[]
  platforms: Platform[]
  total_articles: number
  new_24h: number
  new_7d: number
  source_count: number
  last_refreshed: string | null
}

export type ArticlePage = { total: number; items: Article[]; category_counts: Record<string, number> }

export type BenchmarkCategory = { key: string; label: string; weight: number }

export type HfEval = {
  benchmark: string
  task: string | null
  value: number | string
  verified: boolean
  source: string | null
}

/** Hugging Face info for an open-weight model; stats are absent if the HF API call failed. */
export type HuggingFace = {
  repo: string
  url: string
  /** last 30 days */
  downloads?: number | null
  likes?: number | null
  trending?: number | null
  license?: string | null
  params?: number | null
  updated?: string | null
  evals?: HfEval[]
}

export type Benchmark = {
  id: string
  model: string
  provider: string
  tier: 'Frontier' | 'Open Source'
  url: string | null
  overall: number | null
  scores: Record<string, number | null>
  cost: number | null
  hf: HuggingFace | null
}

export type BenchmarksResponse = {
  source: string
  release: string | null
  /** false when serving the saved offline snapshot instead of live LiveBench data */
  live: boolean
  fetched_at: string | null
  last_error: string | null
  categories: BenchmarkCategory[]
  items: Benchmark[]
  colors: Record<string, string>
}

export type ToolRelease = {
  platform: string
  tier: string
  model: string
  notes: string
  color: string
  release: string | null
  released: string | null
  link: string | null
}

export type Status = {
  running: boolean
  done: number
  total: number
  current: string
  errors: string[]
  last_finished: string | null
  last_refreshed: string | null
}

export type Digest = {
  total: number
  count: number
  subject: string
  html: string
  teams: string
  text: string
}

export async function getJSON<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(path, { signal })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export async function postJSON<T>(path: string): Promise<T> {
  const res = await fetch(path, { method: 'POST' })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

type FetchState<T> = { data?: T; error?: string; loading: boolean }

/** Fetches `url` (re-fetching when it or any of `deps` change), aborting stale requests. */
export function useFetch<T>(url: string | null, deps: unknown[] = []): FetchState<T> {
  const [state, setState] = useState<FetchState<T>>({ loading: url !== null })

  useEffect(() => {
    if (url === null) return
    const ac = new AbortController()
    setState((s) => ({ ...s, loading: true, error: undefined }))
    getJSON<T>(url, ac.signal)
      .then((data) => setState({ data, loading: false }))
      .catch((e: unknown) => {
        if (ac.signal.aborted) return
        setState((s) => ({ ...s, loading: false, error: e instanceof Error ? e.message : String(e) }))
      })
    return () => ac.abort()
  }, [url, ...deps])

  return state
}
