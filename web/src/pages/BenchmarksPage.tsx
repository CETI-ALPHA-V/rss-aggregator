import {
  AlertCircle, AlertTriangle, ArrowDown, ArrowUp, Check, ExternalLink as ExternalIcon, RadioTower, Search, SearchX, X,
} from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'
import {
  CartesianGrid, Legend, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer,
  Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
} from 'recharts'
import { HfCell, HuggingFacePanel } from '../components/HuggingFace'
import {
  Avatar, Badge, Button, Card, Chip, EmptyState, ExternalLink, PageHeader, Segmented, Skeleton, cn,
} from '../components/ui'
import { useFetch, type Benchmark, type BenchmarkCategory, type BenchmarksResponse, type ToolRelease } from '../lib/api'
import { toggle } from '../lib/filters'
import { colorFor, parseDate, relativeTime } from '../lib/format'
import { useRefresh } from '../lib/refresh'

type Column = {
  key: string
  label: string
  title: string
  kind: 'overall' | 'category' | 'cost'
  get: (m: Benchmark) => number | null
}
type SortKey = string // a column key, or 'model'
type TierFilter = 'all' | Benchmark['tier']

const COMPARE_COLORS = ['#2dd4bf', '#a78bfa', '#f59e0b']
const MAX_COMPARE = 3
const SHORT_LABELS: Record<string, string> = {
  'Long Agentic': 'Agentic',
  'Data Analysis': 'Data',
  'Instruction Following': 'IF',
  'Agentic Coding': 'Agentic',
  Mathematics: 'Math',
}

const fmtScore = (n: number | null) => (n === null ? '—' : n.toFixed(1))
const fmtCost = (n: number | null) => (n === null ? '—' : `$${n < 0.1 ? n.toFixed(3) : n.toFixed(2)}`)
const fmtWeight = (w: number) => `×${Number.isInteger(w) ? w : w.toFixed(1)}`

// LiveBench categories can change between releases, so columns come from the data.
function buildColumns(categories: BenchmarkCategory[]): Column[] {
  const weighted = categories.some((c) => c.weight !== 1)
  return [
    {
      key: 'overall',
      label: 'Overall',
      title: weighted ? 'Overall — weighted average of the categories' : 'Overall — average of the categories',
      kind: 'overall',
      get: (m) => m.overall,
    },
    ...categories.map<Column>((c) => ({
      key: c.key,
      label: SHORT_LABELS[c.label] ?? c.label,
      title: c.weight !== 1 ? `${c.label} (counts ${fmtWeight(c.weight)} in Overall)` : c.label,
      kind: 'category',
      get: (m) => m.scores[c.key] ?? null,
    })),
    { key: 'cost', label: 'Cost', title: 'Cost per successful task (USD)', kind: 'cost', get: (m) => m.cost },
  ]
}

function TierBadge({ tier }: { tier: Benchmark['tier'] }) {
  return <Badge tone={tier === 'Frontier' ? 'violet' : 'green'}>{tier === 'Frontier' ? 'Frontier' : 'Open weights'}</Badge>
}

function StatTile({
  label,
  hint,
  model,
  value,
  color,
}: {
  label: string
  hint?: string
  model?: Benchmark
  value: ReactNode
  color: string
}) {
  return (
    <Card className="p-4">
      <p className="text-xs font-medium uppercase tracking-wider text-muted" title={hint}>
        {label}
      </p>
      {model ? (
        <>
          <p className="mt-2 text-2xl font-semibold tabular-nums tracking-tight">{value}</p>
          <p className="mt-1 flex items-center gap-1.5 truncate text-sm text-muted" title={model.model}>
            <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: color }} />
            <span className="truncate">{model.model}</span>
          </p>
        </>
      ) : (
        <p className="mt-2 text-sm text-subtle">No models in view</p>
      )}
    </Card>
  )
}

function maxBy(items: Benchmark[], score: (m: Benchmark) => number | null): Benchmark | undefined {
  let best: Benchmark | undefined
  let bestScore = -Infinity
  for (const m of items) {
    const s = score(m)
    if (s !== null && s > bestScore) {
      best = m
      bestScore = s
    }
  }
  return best
}

function QualityCostChart({ models, colors }: { models: Benchmark[]; colors: Record<string, string> }) {
  const points = models.filter((m) => m.cost !== null && m.cost > 0 && m.overall !== null)
  const byProvider = useMemo(() => {
    const groups = new Map<string, Benchmark[]>()
    for (const m of points) groups.set(m.provider, [...(groups.get(m.provider) ?? []), m])
    return [...groups.entries()]
  }, [points])

  if (points.length === 0) return <p className="py-10 text-center text-sm text-muted">No cost data for these models.</p>

  const costs = points.map((m) => m.cost as number)
  const minCost = Math.min(...costs) * 0.8
  const maxCost = Math.max(...costs) * 1.25
  const ticks = [0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20].filter((t) => t >= minCost && t <= maxCost)

  return (
    <ResponsiveContainer width="100%" height={340}>
      <ScatterChart margin={{ top: 8, right: 16, bottom: 24, left: 0 }}>
        <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
        <XAxis
          type="number"
          dataKey="cost"
          scale="log"
          domain={[minCost, maxCost]}
          ticks={ticks}
          tickFormatter={(v: number) => `$${v}`}
          tick={{ fill: 'var(--muted)', fontSize: 12 }}
          stroke="var(--border)"
          allowDataOverflow
          label={{ value: 'Cost per successful task (log scale)', position: 'insideBottom', offset: -14, fill: 'var(--subtle)', fontSize: 12 }}
        />
        <YAxis
          type="number"
          dataKey="overall"
          domain={[(min: number) => Math.floor(min - 2), (max: number) => Math.ceil(max + 1)]}
          tick={{ fill: 'var(--muted)', fontSize: 12 }}
          stroke="var(--border)"
          width={44}
        />
        <ZAxis range={[70, 70]} />
        <Tooltip
          cursor={{ strokeDasharray: '3 3', stroke: 'var(--subtle)' }}
          content={({ active, payload }) => {
            const m = active ? (payload?.[0]?.payload as Benchmark | undefined) : undefined
            if (!m) return null
            return (
              <div className="rounded-lg border border-border bg-surface px-3 py-2 text-sm shadow-lg">
                <p className="font-medium">{m.model}</p>
                <p className="text-muted">
                  {m.provider} · {fmtScore(m.overall)} overall · {fmtCost(m.cost)}
                </p>
              </div>
            )
          }}
        />
        {byProvider.map(([provider, items]) => (
          <Scatter key={provider} name={provider} data={items} fill={colorFor(provider, colors)} fillOpacity={0.85} />
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  )
}

function ComparePanel({ models, columns, onClear }: { models: Benchmark[]; columns: Column[]; onClear: () => void }) {
  const categoryColumns = columns.filter((c) => c.kind === 'category')
  const data = categoryColumns.map((c) => ({
    category: c.label,
    ...Object.fromEntries(models.map((m, i) => [`m${i}`, c.get(m) ?? 0])),
  }))

  return (
    <Card className="mb-6 p-4 sm:p-5">
      <div className="mb-2 flex items-center justify-between gap-3">
        <h2 className="font-semibold">Comparing {models.length} models</h2>
        <Button variant="ghost" size="sm" onClick={onClear}>
          <X className="h-4 w-4" /> Clear
        </Button>
      </div>
      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <ResponsiveContainer width="100%" height={300}>
          <RadarChart data={data} outerRadius="72%">
            <PolarGrid stroke="var(--border)" />
            <PolarAngleAxis dataKey="category" tick={{ fill: 'var(--muted)', fontSize: 12 }} />
            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
            {models.map((m, i) => (
              // Model names contain dots ("GPT-6.1"), which recharts would read as nested paths — hence index keys.
              <Radar
                key={m.id}
                name={m.model}
                dataKey={`m${i}`}
                stroke={COMPARE_COLORS[i]}
                fill={COMPARE_COLORS[i]}
                fillOpacity={0.12}
                strokeWidth={2}
              />
            ))}
            <Legend wrapperStyle={{ fontSize: 12 }} />
          </RadarChart>
        </ResponsiveContainer>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-muted">
                <th className="py-2 pr-3 font-medium">Category</th>
                {models.map((m, i) => (
                  <th key={m.id} className="px-2 py-2 text-right font-medium">
                    <span className="inline-flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full" style={{ background: COMPARE_COLORS[i] }} />
                      <span className="max-w-[8rem] truncate" title={m.model}>{m.model}</span>
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {columns.map((c) => {
                const values = models.map((m) => c.get(m)).filter((v): v is number => v !== null)
                const best = values.length ? (c.kind === 'cost' ? Math.min(...values) : Math.max(...values)) : null
                return (
                  <tr key={c.key}>
                    <td className="py-2 pr-3 text-muted">{c.kind === 'category' ? c.title : c.label}</td>
                    {models.map((m) => (
                      <td
                        key={m.id}
                        className={cn('px-2 py-2 text-right tabular-nums', c.get(m) === best && 'font-semibold text-accent')}
                      >
                        {c.kind === 'cost' ? fmtCost(c.get(m)) : fmtScore(c.get(m))}
                      </td>
                    ))}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </Card>
  )
}

function ToolReleases({ items }: { items: ToolRelease[] }) {
  return (
    <section className="mt-10">
      <h2 className="text-lg font-semibold tracking-tight">Latest SDK &amp; tool releases</h2>
      <p className="mt-1 text-sm text-muted">
        The newest release-notes entry from each provider&apos;s feeds — usually an SDK or CLI version, not a model version.
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((t) => {
          const date = parseDate(t.released)
          return (
            <Card key={t.platform} className="min-w-0 p-4">
              <div className="flex items-center gap-3">
                <Avatar name={t.platform} color={t.color} size={32} />
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{t.platform}</p>
                  <p className="truncate text-xs text-muted">{t.model ? `Flagship: ${t.model}` : t.notes}</p>
                </div>
              </div>
              <div className="mt-3 rounded-lg bg-surface-2 px-3 py-2 text-sm">
                {t.release ? (
                  <div className="flex items-center justify-between gap-3">
                    {t.link ? (
                      <ExternalLink href={t.link} className="min-w-0 truncate font-medium hover:text-accent" title={t.release}>
                        {t.release}
                      </ExternalLink>
                    ) : (
                      <span className="truncate font-medium">{t.release}</span>
                    )}
                    {date && <span className="shrink-0 text-xs text-subtle">{relativeTime(date)}</span>}
                  </div>
                ) : (
                  <span className="text-subtle">No releases cached yet</span>
                )}
              </div>
            </Card>
          )
        })}
      </div>
    </section>
  )
}

function SourceLine({ data }: { data: BenchmarksResponse }) {
  const fetched = parseDate(data.fetched_at)
  return (
    <span className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1">
      <ExternalLink href="https://livebench.ai/#/" className="inline-flex items-center gap-1 text-accent hover:underline">
        {data.source}
        <ExternalIcon className="h-3 w-3" />
      </ExternalLink>
      {data.live ? (
        <span className="inline-flex items-center gap-1 text-subtle">
          <RadioTower className="h-3.5 w-3.5" />
          Updates automatically{fetched && ` · checked ${relativeTime(fetched)}`}
        </span>
      ) : (
        <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400">
          <AlertTriangle className="h-3.5 w-3.5" />
          Showing a saved snapshot — couldn&apos;t reach LiveBench
        </span>
      )}
    </span>
  )
}

export default function BenchmarksPage() {
  const { version } = useRefresh()
  const bench = useFetch<BenchmarksResponse>('/api/benchmarks', [version])
  const tools = useFetch<{ items: ToolRelease[] }>('/api/tool-releases', [version])

  const [query, setQuery] = useState('')
  const [providers, setProviders] = useState<string[]>([])
  const [tier, setTier] = useState<TierFilter>('all')
  const [sort, setSort] = useState<{ key: SortKey; dir: 'asc' | 'desc' }>({ key: 'overall', dir: 'desc' })
  const [compare, setCompare] = useState<string[]>([])

  const all = bench.data?.items ?? []
  const colors = bench.data?.colors ?? {}
  const columns = useMemo(() => buildColumns(bench.data?.categories ?? []), [bench.data])
  const providerList = useMemo(() => [...new Set(all.map((m) => m.provider))].sort(), [all])

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase()
    const rows = all.filter(
      (m) =>
        (providers.length === 0 || providers.includes(m.provider)) &&
        (tier === 'all' || m.tier === tier) &&
        (!needle || m.model.toLowerCase().includes(needle) || m.provider.toLowerCase().includes(needle)),
    )
    const dir = sort.dir === 'asc' ? 1 : -1
    if (sort.key === 'model') return rows.sort((a, b) => a.model.localeCompare(b.model) * dir)
    const get =
      sort.key === 'downloads'
        ? (m: Benchmark) => m.hf?.downloads ?? null
        : columns.find((c) => c.key === sort.key)?.get
    if (!get) return rows
    // Missing values always sink to the bottom, whichever way the column is sorted.
    return rows.sort((a, b) => {
      const va = get(a)
      const vb = get(b)
      if (va === null) return vb === null ? 0 : 1
      if (vb === null) return -1
      return (va - vb) * dir
    })
  }, [all, providers, tier, query, sort, columns])

  // Top three values per column among visible rows (lowest for cost).
  const leaders = useMemo(() => {
    const out: Record<string, Set<number>> = {}
    for (const c of columns) {
      const values = [...new Set(visible.map(c.get).filter((v): v is number => v !== null))]
      values.sort((a, b) => (c.kind === 'cost' ? a - b : b - a))
      out[c.key] = new Set(values.slice(0, 3))
    }
    return out
  }, [visible, columns])

  const compared = compare.map((id) => all.find((m) => m.id === id)).filter((m): m is Benchmark => !!m)
  const filtersActive = query !== '' || providers.length > 0 || tier !== 'all'

  const onSort = (key: SortKey) =>
    setSort((s) =>
      s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: key === 'cost' || key === 'model' ? 'asc' : 'desc' },
    )

  const categories = bench.data?.categories ?? []
  const headline = categories.reduce<BenchmarkCategory | undefined>((best, c) => (!best || c.weight > best.weight ? c : best), undefined)
  const topOverall = maxBy(visible, (m) => m.overall)
  // Pure score-per-dollar always crowns a cheap, weak model, so only consider models
  // within 10% of the best overall score in view.
  const valueFloor = (topOverall?.overall ?? 0) * 0.9
  const bestValue = maxBy(visible, (m) =>
    m.overall !== null && m.cost && m.overall >= valueFloor ? m.overall / m.cost : null,
  )
  const topOpen = maxBy(visible.filter((m) => m.tier === 'Open Source'), (m) => m.overall)
  const topHeadline = headline ? maxBy(visible, (m) => m.scores[headline.key] ?? null) : undefined
  const colorOf = (m?: Benchmark) => (m ? colorFor(m.provider, colors) : 'transparent')
  const weightNote = categories.filter((c) => c.weight !== 1).map((c) => `${c.label} ${fmtWeight(c.weight)}`)

  if (bench.error) {
    return (
      <Card>
        <EmptyState icon={<AlertCircle className="h-5 w-5" />} title="Couldn't load benchmarks">
          {bench.error}. Is the API server running on port 8000?
        </EmptyState>
      </Card>
    )
  }

  return (
    <>
      <PageHeader
        title="AI Benchmarks"
        description={
          <>
            How today&apos;s top LLMs score on LiveBench across{' '}
            {categories.length ? categories.map((c) => c.label.toLowerCase()).join(', ') : 'its categories'} (0–100), and what
            each costs to run.
            {bench.data && <SourceLine data={bench.data} />}
          </>
        }
      />

      {bench.loading && !bench.data ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
      ) : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatTile label="Top overall" model={topOverall} value={topOverall && fmtScore(topOverall.overall)} color={colorOf(topOverall)} />
            <StatTile
              label="Best value (top tier)"
              hint="Highest score per dollar among models within 10% of the top overall score"
              model={bestValue}
              value={bestValue && (
                <>
                  {fmtScore(bestValue.overall)}
                  <span className="ml-1.5 whitespace-nowrap text-sm font-normal text-muted">at {fmtCost(bestValue.cost)}</span>
                </>
              )}
              color={colorOf(bestValue)}
            />
            <StatTile label="Top open-weights" model={topOpen} value={topOpen && fmtScore(topOpen.overall)} color={colorOf(topOpen)} />
            {headline && (
              <StatTile
                label={`Top ${headline.label.toLowerCase()}`}
                model={topHeadline}
                value={topHeadline && fmtScore(topHeadline.scores[headline.key] ?? null)}
                color={colorOf(topHeadline)}
              />
            )}
          </div>

          <Card className="mb-6 space-y-3 p-3 sm:p-4">
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative w-full sm:w-auto sm:flex-1">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle" />
                <input
                  type="search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search models or companies — e.g. Claude, GPT, Gemini…"
                  aria-label="Search models"
                  className="h-9 w-full rounded-lg border border-border bg-bg pl-9 pr-3 text-sm outline-none placeholder:text-subtle focus:border-accent"
                />
              </div>
              <Segmented
                label="Tier"
                value={tier}
                onChange={setTier}
                options={[
                  { label: 'All', value: 'all' },
                  { label: 'Frontier', value: 'Frontier' },
                  { label: 'Open weights', value: 'Open Source' },
                ]}
              />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {providerList.map((p) => (
                <Chip key={p} active={providers.includes(p)} color={colorFor(p, colors)} onClick={() => setProviders(toggle(providers, p))}>
                  {p}
                </Chip>
              ))}
              {filtersActive && (
                <button
                  type="button"
                  onClick={() => {
                    setQuery('')
                    setProviders([])
                    setTier('all')
                  }}
                  className="ml-auto inline-flex items-center gap-1 text-sm text-muted hover:text-fg"
                >
                  <X className="h-3.5 w-3.5" /> Clear filters
                </button>
              )}
            </div>
          </Card>

          {compared.length >= 2 && <ComparePanel models={compared} columns={columns} onClear={() => setCompare([])} />}

          {visible.length === 0 ? (
            <Card>
              <EmptyState icon={<SearchX className="h-5 w-5" />} title="No models match these filters" />
            </Card>
          ) : (
            <>
              <Card className="mb-6 p-4 sm:p-5">
                <h2 className="font-semibold">Quality vs. cost</h2>
                <p className="mb-2 text-sm text-muted">Up and to the left is better: a higher overall score for less money per task.</p>
                <QualityCostChart models={visible} colors={colors} />
              </Card>

              <Card className="overflow-hidden">
                <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3 sm:px-5">
                  <h2 className="font-semibold">
                    Leaderboard <span className="ml-1 text-sm font-normal text-muted">{visible.length} models</span>
                  </h2>
                  <p className="text-xs text-muted">
                    {compare.length === 0
                      ? `Select up to ${MAX_COMPARE} models to compare`
                      : `${compare.length}/${MAX_COMPARE} selected${compare.length < 2 ? ' — pick one more' : ''}`}
                  </p>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[1080px] text-sm">
                    <thead>
                      <tr className="border-b border-border text-xs text-muted">
                        <th className="sticky left-0 z-10 bg-surface py-2.5 pl-4 pr-2 text-left font-medium sm:pl-5">
                          <SortHeader label="Model" active={sort.key === 'model'} dir={sort.dir} onClick={() => onSort('model')} />
                        </th>
                        <th className="px-2 py-2.5 text-left font-medium">Company</th>
                        {columns.map((c) => (
                          <th key={c.key} className="px-2 py-2.5 text-right font-medium" title={c.title}>
                            <SortHeader label={c.label} active={sort.key === c.key} dir={sort.dir} onClick={() => onSort(c.key)} alignRight />
                          </th>
                        ))}
                        <th
                          className="py-2.5 pl-3 pr-4 text-left font-medium sm:pr-5"
                          title="Hugging Face downloads (last 30 days) and licence — open-weight models only"
                        >
                          <SortHeader label="Hugging Face" active={sort.key === 'downloads'} dir={sort.dir} onClick={() => onSort('downloads')} />
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {visible.map((m) => {
                        const selected = compare.includes(m.id)
                        const full = !selected && compare.length >= MAX_COMPARE
                        return (
                          <tr key={m.id} className={cn('group', selected && 'bg-accent-soft/60')}>
                            <td
                              className={cn(
                                'sticky left-0 z-10 py-2.5 pl-4 pr-2 sm:pl-5',
                                selected ? 'bg-accent-soft' : 'bg-surface group-hover:bg-surface-2',
                              )}
                            >
                              <div className="flex items-center gap-3">
                                <button
                                  type="button"
                                  onClick={() => setCompare(toggle(compare, m.id))}
                                  disabled={full}
                                  aria-label={`${selected ? 'Remove' : 'Add'} ${m.model} ${selected ? 'from' : 'to'} comparison`}
                                  title={full ? `You can compare up to ${MAX_COMPARE} models` : 'Compare'}
                                  className={cn(
                                    'grid h-4 w-4 shrink-0 place-items-center rounded border transition-colors disabled:opacity-40',
                                    selected ? 'border-accent bg-accent text-accent-fg' : 'border-border hover:border-accent',
                                  )}
                                >
                                  {selected && <Check className="h-3 w-3" strokeWidth={3} />}
                                </button>
                                <div className="min-w-0">
                                  {m.url ? (
                                    <ExternalLink
                                      href={m.url}
                                      className="block max-w-[16rem] truncate font-medium hover:text-accent"
                                      title={m.model}
                                    >
                                      {m.model}
                                    </ExternalLink>
                                  ) : (
                                    <p className="max-w-[16rem] truncate font-medium" title={m.model}>{m.model}</p>
                                  )}
                                  <div className="mt-0.5"><TierBadge tier={m.tier} /></div>
                                </div>
                              </div>
                            </td>
                            <td className="px-2 py-2.5 group-hover:bg-surface-2">
                              <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-muted">
                                <span className="h-2 w-2 rounded-full" style={{ background: colorFor(m.provider, colors) }} />
                                {m.provider}
                              </span>
                            </td>
                            {columns.map((c) => {
                              const v = c.get(m)
                              const lead = v !== null && leaders[c.key]?.has(v)
                              return (
                                <td
                                  key={c.key}
                                  className={cn(
                                    'px-2 py-2.5 text-right tabular-nums group-hover:bg-surface-2',
                                    c.kind === 'overall' && 'font-semibold',
                                    lead ? 'text-accent' : 'text-fg/85',
                                  )}
                                >
                                  <span className={cn(lead && 'rounded bg-accent-soft px-1.5 py-0.5')}>
                                    {c.kind === 'cost' ? fmtCost(v) : fmtScore(v)}
                                  </span>
                                </td>
                              )
                            })}
                            <td className="py-2.5 pl-3 pr-4 group-hover:bg-surface-2 sm:pr-5">
                              <HfCell model={m} />
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
                <p className="border-t border-border px-4 py-3 text-xs text-muted sm:px-5">
                  {weightNote.length > 0 && <>Overall is LiveBench&apos;s weighted average ({weightNote.join(', ')}, everything else ×1). </>}
                  Highlighted cells are the top three in each column. Cost is LiveBench&apos;s cost per successful task.
                </p>
              </Card>

              <HuggingFacePanel models={visible} colors={colors} />
            </>
          )}
        </>
      )}

      {tools.data && <ToolReleases items={tools.data.items} />}
    </>
  )
}

function SortHeader({
  label,
  active,
  dir,
  onClick,
  alignRight,
}: {
  label: string
  active: boolean
  dir: 'asc' | 'desc'
  onClick: () => void
  alignRight?: boolean
}) {
  const Icon = dir === 'asc' ? ArrowUp : ArrowDown
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn('inline-flex items-center gap-1 whitespace-nowrap hover:text-fg', active && 'text-fg', alignRight && 'flex-row-reverse')}
    >
      {label}
      <Icon className={cn('h-3 w-3', !active && 'opacity-0')} />
    </button>
  )
}
