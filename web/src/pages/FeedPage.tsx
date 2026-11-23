import { AlertCircle, Info, LayoutGrid, List, Mail, Play, Search, SearchX, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { IntroHero } from '../components/IntroHero'
import { PlatformPicker } from '../components/PlatformPicker'
import {
  Avatar, Button, Card, Chip, EmptyState, ExternalLink, Segmented, Skeleton, TypeBadge,
  buttonClasses, cn,
} from '../components/ui'
import { getJSON, useFetch, type Article, type ArticlePage, type Meta } from '../lib/api'
import {
  DAY_OPTIONS, TYPE_OPTIONS, hasActiveFilters, readFilters, toApiParams, toggle, writeFilters, type Filters,
} from '../lib/filters'
import { dayKey, dayLabel, domainOf, fullDate, parseDate, plural, relativeTime, youtubeId } from '../lib/format'
import { useRefresh } from '../lib/refresh'

const PAGE_SIZE = 50
const INTRO_DISMISSED_KEY = 'maintain-intro-dismissed'
const COMPANY_CHIP_LIMIT = 12

type View = 'list' | 'cards'

function ArticleMeta({ article, color }: { article: Article; color: string }) {
  const date = parseDate(article.published)
  const domain = domainOf(article.link)
  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
      <span className="inline-flex items-center gap-1.5 font-medium text-fg/80">
        <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
        {article.platform}
      </span>
      {domain && <span className="hidden text-subtle sm:inline">{domain}</span>}
      <TypeBadge type={article.type} />
      {date && (
        <time dateTime={article.published ?? undefined} title={fullDate(date)} className="ml-auto whitespace-nowrap text-subtle">
          {relativeTime(date)}
        </time>
      )}
    </div>
  )
}

function VideoThumbnail({ article, className }: { article: Article; className?: string }) {
  const id = youtubeId(article.link)
  if (!id) return null
  return (
    <ExternalLink
      href={article.link}
      aria-label={`Watch: ${article.title}`}
      className={cn('group/thumb relative block shrink-0 overflow-hidden rounded-lg bg-surface-2', className)}
    >
      <img
        src={`https://i.ytimg.com/vi/${id}/mqdefault.jpg`}
        alt=""
        loading="lazy"
        className="aspect-video h-full w-full object-cover transition-transform duration-300 group-hover/thumb:scale-105"
      />
      <span className="absolute inset-0 grid place-items-center">
        <span className="grid h-9 w-9 place-items-center rounded-full bg-black/65 text-white shadow">
          <Play className="ml-0.5 h-4 w-4 fill-current" />
        </span>
      </span>
    </ExternalLink>
  )
}

function ArticleRow({ article, color }: { article: Article; color: string }) {
  return (
    <article className="flex gap-4 px-4 py-4 sm:px-5">
      <Avatar name={article.platform} color={color} />
      <div className="min-w-0 flex-1">
        <ArticleMeta article={article} color={color} />
        <ExternalLink
          href={article.link}
          className="mt-1 block font-medium leading-snug text-fg decoration-accent/40 underline-offset-2 hover:text-accent hover:underline"
        >
          {article.title || '(untitled)'}
        </ExternalLink>
        {article.summary && <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-muted">{article.summary}</p>}
      </div>
      <VideoThumbnail article={article} className="mt-5 w-28 self-start sm:w-40" />
    </article>
  )
}

function ArticleCard({ article, color }: { article: Article; color: string }) {
  return (
    <Card className="flex flex-col p-4 transition-shadow hover:shadow-md hover:shadow-black/5">
      <VideoThumbnail article={article} className="-mx-4 -mt-4 mb-3 rounded-b-none rounded-t-xl" />
      <div className="flex items-center gap-3">
        <Avatar name={article.platform} color={color} size={28} />
        <div className="min-w-0 flex-1">
          <ArticleMeta article={article} color={color} />
        </div>
      </div>
      <ExternalLink href={article.link} className="mt-3 font-medium leading-snug hover:text-accent">
        {article.title || '(untitled)'}
      </ExternalLink>
      {article.summary && <p className="mt-1.5 line-clamp-3 text-sm leading-relaxed text-muted">{article.summary}</p>}
    </Card>
  )
}

function LoadingList() {
  return (
    <Card className="divide-y divide-border">
      {Array.from({ length: 6 }, (_, i) => (
        <div key={i} className="flex gap-4 px-5 py-4">
          <Skeleton className="h-9 w-9 shrink-0 rounded-lg" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3 w-40" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-full" />
          </div>
        </div>
      ))}
    </Card>
  )
}

export default function FeedPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = readFilters(searchParams)
  const view: View = searchParams.get('view') === 'cards' ? 'cards' : 'list'
  const { version } = useRefresh()

  const meta = useFetch<Meta>('/api/meta', [version])
  const colors = useMemo(
    () => Object.fromEntries((meta.data?.platforms ?? []).map((p) => [p.name, p.color])),
    [meta.data],
  )

  const update = (patch: Partial<Filters>) =>
    setSearchParams(writeFilters({ ...filters, ...patch }, searchParams), { replace: true })
  const setView = (v: View) => {
    const next = new URLSearchParams(searchParams)
    if (v === 'cards') next.set('view', 'cards')
    else next.delete('view')
    setSearchParams(next, { replace: true })
  }

  // Search input is local state, debounced into the URL.
  const [search, setSearch] = useState(filters.q)
  useEffect(() => setSearch(filters.q), [filters.q])
  useEffect(() => {
    if (search === filters.q) return
    const t = window.setTimeout(() => update({ q: search }), 300)
    return () => window.clearTimeout(t)
  }, [search])

  const apiQuery = toApiParams(filters).toString()
  const [items, setItems] = useState<Article[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string>()
  const [attempt, setAttempt] = useState(0)
  const [categoryCounts, setCategoryCounts] = useState<Record<string, number>>()

  useEffect(() => {
    const ac = new AbortController()
    setLoading(true)
    setError(undefined)
    getJSON<ArticlePage>(`/api/articles?${apiQuery}&limit=${PAGE_SIZE}`, ac.signal)
      .then((page) => {
        setItems(page.items)
        setTotal(page.total)
        setCategoryCounts(page.category_counts)
        setLoading(false)
      })
      .catch((e: Error) => {
        if (ac.signal.aborted) return
        setError(e.message)
        setLoading(false)
      })
    return () => ac.abort()
  }, [apiQuery, version, attempt])

  const loadMore = async () => {
    setLoadingMore(true)
    try {
      const page = await getJSON<ArticlePage>(`/api/articles?${apiQuery}&limit=${PAGE_SIZE}&offset=${items.length}`)
      setItems((prev) => [...prev, ...page.items])
      setTotal(page.total)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoadingMore(false)
    }
  }

  const groups = useMemo(() => {
    const out: { key: string; label: string; items: Article[] }[] = []
    for (const article of items) {
      const date = parseDate(article.published)
      const key = dayKey(date)
      let group = out[out.length - 1]
      if (!group || group.key !== key) {
        group = { key, label: dayLabel(date), items: [] }
        out.push(group)
      }
      group.items.push(article)
    }
    return out
  }, [items])

  const activeCategory = filters.categories.length === 1 ? filters.categories[0] : null
  const allPlatforms = meta.data?.platforms ?? []
  const tabPlatforms = activeCategory ? allPlatforms.filter((p) => p.categories.includes(activeCategory)) : allPlatforms

  // Company chips: busiest sources first; on large tabs show the top few plus anything selected.
  const [showAllCompanies, setShowAllCompanies] = useState(false)
  const companies = [...tabPlatforms].sort((a, b) => b.articles - a.articles)
  const collapsible = companies.length > COMPANY_CHIP_LIMIT + 3
  const visibleCompanies =
    showAllCompanies || !collapsible
      ? companies
      : companies.filter((p, i) => i < COMPANY_CHIP_LIMIT || filters.platforms.includes(p.name))
  const hiddenCompanies = companies.length - visibleCompanies.length

  const selectTab = (category: string | null) => {
    // Drop selected platforms that don't publish in the new tab, or it would show nothing.
    const inTab = (name: string) =>
      !category || allPlatforms.find((p) => p.name === name)?.categories.includes(category)
    update({ categories: category ? [category] : [], platforms: filters.platforms.filter(inTab) })
  }

  const tabs: { key: string | null; label: string; count?: number }[] = [
    {
      key: null,
      label: 'All',
      count: categoryCounts && Object.values(categoryCounts).reduce((a, b) => a + b, 0),
    },
    ...(meta.data?.categories ?? []).map((c) => ({ key: c, label: c, count: categoryCounts?.[c] ?? (categoryCounts && 0) })),
  ]

  const [showIntro, setShowIntro] = useState(() => {
    try {
      return localStorage.getItem(INTRO_DISMISSED_KEY) !== '1'
    } catch {
      return true
    }
  })
  const setIntro = (show: boolean) => {
    setShowIntro(show)
    try {
      if (show) localStorage.removeItem(INTRO_DISMISSED_KEY)
      else localStorage.setItem(INTRO_DISMISSED_KEY, '1')
    } catch {
      // Storage unavailable; the intro just reappears next visit.
    }
  }

  // Clearing keeps the current tab; the tab is navigation, not a filter.
  const clearAll = () => update({ platforms: [], type: 'all', q: '' })
  const active = hasActiveFilters({ ...filters, categories: [] })
  const digestLink = `/digest${searchParams.toString() ? `?${searchParams}` : ''}`

  const FeedHeading = showIntro ? 'h2' : 'h1'

  return (
    <>
      {showIntro && <IntroHero platformCount={meta.data?.platforms.length} onDismiss={() => setIntro(false)} />}

      <div id="latest" className="mb-5 flex scroll-mt-24 flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <FeedHeading className="text-2xl font-semibold tracking-tight">What&apos;s new</FeedHeading>
          <p className="mt-1 text-sm text-muted">
            {meta.data ? (
              <>
                <span className="font-semibold text-fg">{meta.data.new_24h.toLocaleString()}</span> updates in the last
                24 hours · <span className="font-semibold text-fg">{meta.data.new_7d.toLocaleString()}</span> this week ·
                tracking {meta.data.source_count} sources from {meta.data.platforms.length} platforms
              </>
            ) : (
              'The latest releases, posts and videos from the platforms you build on.'
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {!showIntro && (
            <Button variant="ghost" size="sm" onClick={() => setIntro(true)}>
              <Info className="h-4 w-4" />
              What is m[AI]ntain?
            </Button>
          )}
          <Link to={digestLink} className={buttonClasses('primary')}>
            <Mail className="h-4 w-4" />
            Create digest
          </Link>
        </div>
      </div>

      <div
        role="tablist"
        aria-label="Category"
        className="-mx-4 mb-4 flex gap-1 overflow-x-auto border-b border-border px-4 [scrollbar-width:none] sm:mx-0 sm:px-0"
      >
        {tabs.map((tab) => {
          const selected = tab.key === activeCategory && (tab.key !== null || filters.categories.length === 0)
          return (
            <button
              key={tab.label}
              type="button"
              role="tab"
              aria-selected={selected}
              onClick={() => selectTab(tab.key)}
              className={cn(
                '-mb-px inline-flex shrink-0 items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors',
                selected ? 'border-accent text-fg' : 'border-transparent text-muted hover:text-fg',
              )}
            >
              {tab.label}
              {tab.count !== undefined && (
                <span
                  className={cn(
                    'rounded-full px-1.5 py-0.5 text-xs tabular-nums',
                    selected ? 'bg-accent-soft text-accent' : 'bg-surface-2 text-subtle',
                  )}
                >
                  {tab.count.toLocaleString()}
                </span>
              )}
            </button>
          )
        })}
      </div>

      <Card className="mb-6 space-y-3 p-3 sm:p-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative w-full sm:w-auto sm:flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search titles and summaries…"
              aria-label="Search articles"
              className="h-9 w-full rounded-lg border border-border bg-bg pl-9 pr-3 text-sm outline-none transition-colors placeholder:text-subtle focus:border-accent"
            />
          </div>
          <PlatformPicker
            platforms={tabPlatforms}
            selected={filters.platforms}
            onChange={(platforms) => update({ platforms })}
          />
          <Segmented
            label="Layout"
            value={view}
            onChange={setView}
            options={[
              { label: <List className="h-4 w-4" />, value: 'list', title: 'List view' },
              { label: <LayoutGrid className="h-4 w-4" />, value: 'cards', title: 'Card view' },
            ]}
          />
        </div>
        {companies.length > 0 && (
          <div
            role="group"
            aria-label="Companies"
            className="-mx-3 flex items-center gap-1.5 overflow-x-auto px-3 [scrollbar-width:none] sm:mx-0 sm:flex-wrap sm:px-0"
          >
            {visibleCompanies.map((p) => (
              <Chip
                key={p.name}
                active={filters.platforms.includes(p.name)}
                color={p.color}
                onClick={() => update({ platforms: toggle(filters.platforms, p.name) })}
              >
                {p.name}
              </Chip>
            ))}
            {collapsible && (
              <button
                type="button"
                onClick={() => setShowAllCompanies((v) => !v)}
                className="h-7 shrink-0 whitespace-nowrap px-2 text-sm font-medium text-muted hover:text-fg"
              >
                {showAllCompanies ? 'Show fewer' : `+${hiddenCompanies} more`}
              </button>
            )}
          </div>
        )}
        <div className="flex flex-wrap items-center gap-2">
          <Segmented
            label="Date range"
            value={filters.days}
            onChange={(days) => update({ days })}
            options={DAY_OPTIONS.map((o) => ({
              label: (
                <>
                  <span className="sm:hidden">{o.short}</span>
                  <span className="hidden sm:inline">{o.label}</span>
                </>
              ),
              value: o.value,
              title: o.label,
            }))}
          />
          <Segmented label="Content type" value={filters.type} onChange={(type) => update({ type })} options={TYPE_OPTIONS} />
          {active && (
            <button type="button" onClick={clearAll} className="ml-auto inline-flex items-center gap-1 text-sm text-muted hover:text-fg">
              <X className="h-3.5 w-3.5" />
              Clear filters
            </button>
          )}
        </div>
      </Card>

      {!loading && !error && (
        <p className="mb-3 text-sm text-muted">
          Showing {items.length.toLocaleString()} of {plural(total, 'article')}
        </p>
      )}

      {loading ? (
        <LoadingList />
      ) : error ? (
        <Card>
          <EmptyState
            icon={<AlertCircle className="h-5 w-5" />}
            title="Couldn't load articles"
            action={<Button onClick={() => setAttempt((n) => n + 1)}>Try again</Button>}
          >
            {error}. Is the API server running on port 8000?
          </EmptyState>
        </Card>
      ) : items.length === 0 ? (
        <Card>
          <EmptyState
            icon={<SearchX className="h-5 w-5" />}
            title="No articles match these filters"
            action={active ? <Button onClick={clearAll}>Clear filters</Button> : undefined}
          >
            Try a wider date range or fewer filters.
          </EmptyState>
        </Card>
      ) : (
        <div className="space-y-6">
          {groups.map((group) => (
            <section key={group.key}>
              <h2 className="sticky top-18 z-10 -mx-1 mb-2 bg-bg/90 px-1 py-2 text-xs font-semibold uppercase tracking-wider text-muted backdrop-blur">
                {group.label}
                <span className="ml-2 font-normal normal-case tracking-normal text-subtle">{group.items.length}</span>
              </h2>
              {view === 'list' ? (
                <Card className="divide-y divide-border">
                  {group.items.map((a) => (
                    <ArticleRow key={`${a.feed_id}:${a.link}`} article={a} color={colors[a.platform] ?? '#71717a'} />
                  ))}
                </Card>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  {group.items.map((a) => (
                    <ArticleCard key={`${a.feed_id}:${a.link}`} article={a} color={colors[a.platform] ?? '#71717a'} />
                  ))}
                </div>
              )}
            </section>
          ))}
          {items.length < total && (
            <div className="flex justify-center pt-2">
              <Button onClick={loadMore} disabled={loadingMore}>
                {loadingMore ? 'Loading…' : `Load ${Math.min(PAGE_SIZE, total - items.length)} more`}
              </Button>
            </div>
          )}
        </div>
      )}
    </>
  )
}
