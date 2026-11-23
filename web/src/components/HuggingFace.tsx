import { ChevronDown, ExternalLink as ExternalIcon } from 'lucide-react'
import { Fragment, useMemo, useState } from 'react'
import type { Benchmark, HuggingFace } from '../lib/api'
import { colorFor, parseDate, relativeTime } from '../lib/format'
import { Badge, Card, ExternalLink, Segmented, cn } from './ui'

const compact = new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 })
const size = new Intl.NumberFormat('en', { notation: 'compact', maximumSignificantDigits: 3 })

// Licences that clearly allow commercial use. Anything else is shown as "Custom" with a
// prompt to check the terms — we can't vouch for model-specific licences.
const PERMISSIVE: Record<string, string> = {
  mit: 'MIT',
  'apache-2.0': 'Apache 2.0',
  'bsd-2-clause': 'BSD-2',
  'bsd-3-clause': 'BSD-3',
  'cc-by-4.0': 'CC BY 4.0',
}

export const fmtCount = (n?: number | null) => (n == null ? '—' : compact.format(n))
export const fmtParams = (n?: number | null) => (n == null ? '—' : size.format(n))

export function LicenceBadge({ licence }: { licence?: string | null }) {
  if (!licence) return <span className="text-subtle">—</span>
  const permissive = PERMISSIVE[licence.toLowerCase()]
  return permissive ? (
    <span title="Permissive licence — commercial use allowed">
      <Badge tone="green">{permissive}</Badge>
    </span>
  ) : (
    <span title={`Licence: ${licence} — check the terms before commercial use`}>
      <Badge tone="amber">Custom</Badge>
    </span>
  )
}

/** Compact Hugging Face cell for the main leaderboard. */
export function HfCell({ model }: { model: Benchmark }) {
  if (!model.hf) {
    return (
      <span className="text-subtle" title={model.tier === 'Frontier' ? 'Closed model — not on Hugging Face' : 'No Hugging Face repo linked'}>
        —
      </span>
    )
  }
  return (
    <ExternalLink
      href={model.hf.url}
      title={`${model.hf.repo} on Hugging Face`}
      className="inline-flex items-center gap-2 whitespace-nowrap hover:text-accent"
    >
      <span className="tabular-nums">{fmtCount(model.hf.downloads)}</span>
      <LicenceBadge licence={model.hf.license} />
    </ExternalLink>
  )
}

type HfSort = 'overall' | 'downloads' | 'likes'

function EvalList({ hf }: { hf: HuggingFace }) {
  const evals = hf.evals ?? []
  return (
    <div className="flex flex-wrap gap-2 py-1">
      {evals.map((e, i) => {
        const value = typeof e.value === 'number' ? e.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : e.value
        const body = (
          <>
            <span className="text-muted">{e.task && e.task !== e.benchmark ? `${e.benchmark} · ${e.task}` : e.benchmark}</span>
            <span className="font-semibold tabular-nums">{value}</span>
            <Badge tone={e.verified ? 'green' : 'neutral'}>{e.verified ? 'Verified' : 'Self-reported'}</Badge>
          </>
        )
        return e.source ? (
          <ExternalLink
            key={i}
            href={e.source}
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-bg px-2.5 py-1 text-xs hover:border-accent/50"
          >
            {body}
          </ExternalLink>
        ) : (
          <span key={i} className="inline-flex items-center gap-2 rounded-lg border border-border bg-bg px-2.5 py-1 text-xs">
            {body}
          </span>
        )
      })}
    </div>
  )
}

/** LiveBench score side by side with Hugging Face adoption, size and licence. */
export function HuggingFacePanel({ models, colors }: { models: Benchmark[]; colors: Record<string, string> }) {
  const [sort, setSort] = useState<HfSort>('overall')
  const [open, setOpen] = useState<string | null>(null)

  const rows = useMemo(() => {
    const withHf = models.filter((m) => m.hf)
    const key = (m: Benchmark) =>
      sort === 'overall' ? m.overall : sort === 'downloads' ? m.hf?.downloads : m.hf?.likes
    return withHf.sort((a, b) => (key(b) ?? -1) - (key(a) ?? -1))
  }, [models, sort])

  if (rows.length === 0) return null

  return (
    <Card className="mt-6 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3 sm:px-5">
        <div>
          <h2 className="font-semibold">Open-weight models on Hugging Face</h2>
          <p className="text-sm text-muted">
            LiveBench score next to real-world adoption, size and licence — what&apos;s good, popular and usable.
          </p>
        </div>
        <Segmented
          label="Sort open-weight models"
          value={sort}
          onChange={setSort}
          options={[
            { label: 'Score', value: 'overall', title: 'LiveBench overall score' },
            { label: 'Downloads', value: 'downloads', title: 'Hugging Face downloads, last 30 days' },
            { label: 'Likes', value: 'likes', title: 'Hugging Face likes' },
          ]}
        />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted">
              <th className="py-2.5 pl-4 pr-2 font-medium sm:pl-5">Model</th>
              <th className="px-2 py-2.5 text-right font-medium">LiveBench</th>
              <th className="px-2 py-2.5 text-right font-medium" title="Hugging Face downloads in the last 30 days">Downloads / 30d</th>
              <th className="px-2 py-2.5 text-right font-medium">Likes</th>
              <th className="px-2 py-2.5 text-right font-medium" title="Total parameters (from the safetensors metadata)">Size</th>
              <th className="px-2 py-2.5 font-medium">Licence</th>
              <th className="px-2 py-2.5 font-medium">Updated</th>
              <th className="py-2.5 pl-2 pr-4 text-right font-medium sm:pr-5" title="Results Hugging Face lists for this model on other benchmarks">
                Other benchmarks
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((m) => {
              const hf = m.hf as HuggingFace
              const updated = parseDate(hf.updated)
              const evalCount = hf.evals?.length ?? 0
              const expanded = open === m.id
              return (
                <Fragment key={m.id}>
                  <tr className="hover:bg-surface-2">
                    <td className="py-2.5 pl-4 pr-2 sm:pl-5">
                      <ExternalLink href={hf.url} className="group inline-flex max-w-[18rem] items-center gap-2" title={hf.repo}>
                        <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: colorFor(m.provider, colors) }} />
                        <span className="truncate font-medium group-hover:text-accent">{m.model}</span>
                        <ExternalIcon className="h-3 w-3 shrink-0 text-subtle" />
                      </ExternalLink>
                      <p className="ml-4 truncate text-xs text-subtle">{hf.repo}</p>
                    </td>
                    <td className="px-2 py-2.5 text-right font-semibold tabular-nums">{m.overall?.toFixed(1) ?? '—'}</td>
                    <td className="px-2 py-2.5 text-right tabular-nums">{fmtCount(hf.downloads)}</td>
                    <td className="px-2 py-2.5 text-right tabular-nums">{fmtCount(hf.likes)}</td>
                    <td className="px-2 py-2.5 text-right tabular-nums">{fmtParams(hf.params)}</td>
                    <td className="px-2 py-2.5"><LicenceBadge licence={hf.license} /></td>
                    <td className="whitespace-nowrap px-2 py-2.5 text-muted">{updated ? relativeTime(updated) : '—'}</td>
                    <td className="py-2.5 pl-2 pr-4 text-right sm:pr-5">
                      {evalCount > 0 ? (
                        <button
                          type="button"
                          onClick={() => setOpen(expanded ? null : m.id)}
                          aria-expanded={expanded}
                          className="inline-flex items-center gap-1 whitespace-nowrap text-sm text-muted hover:text-fg"
                        >
                          {evalCount} result{evalCount === 1 ? '' : 's'}
                          <ChevronDown className={cn('h-3.5 w-3.5 transition-transform', expanded && 'rotate-180')} />
                        </button>
                      ) : (
                        <span className="text-subtle">—</span>
                      )}
                    </td>
                  </tr>
                  {expanded && (
                    <tr className="bg-surface-2/50">
                      <td colSpan={8} className="px-4 pb-3 sm:px-5">
                        <EvalList hf={hf} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="border-t border-border px-4 py-3 text-xs text-muted sm:px-5">
        From the Hugging Face API, refreshed daily. &ldquo;Other benchmarks&rdquo; are the results Hugging Face lists for each model —
        mostly self-reported and on different tests from LiveBench, so they aren&apos;t comparable with the scores above. Licence badges are a
        guide only: green means a standard permissive licence; check custom licences before commercial use.
      </p>
    </Card>
  )
}
