import { AlertCircle, ArrowLeft, Check, Copy, Download, Inbox, Search, X } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { PlatformPicker } from '../components/PlatformPicker'
import { Button, Card, Chip, EmptyState, PageHeader, Segmented, Skeleton, buttonClasses } from '../components/ui'
import { useFetch, type Digest, type Meta } from '../lib/api'
import { DAY_OPTIONS, TYPE_OPTIONS, readFilters, toApiParams, toggle, writeFilters, type Filters } from '../lib/filters'
import { plural } from '../lib/format'
import { useRefresh } from '../lib/refresh'

type Format = 'outlook' | 'teams' | 'text'

const LIMITS = [10, 25, 50, 100]
const DEFAULT_LIMIT = 25

async function copyRichText(html: string, text: string): Promise<void> {
  if (window.ClipboardItem && navigator.clipboard?.write) {
    await navigator.clipboard.write([
      new ClipboardItem({
        'text/html': new Blob([html], { type: 'text/html' }),
        'text/plain': new Blob([text], { type: 'text/plain' }),
      }),
    ])
  } else {
    await navigator.clipboard.writeText(text)
  }
}

function download(filename: string, content: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function useCopied(): [string | null, (key: string, action: () => Promise<void>) => void] {
  const [copied, setCopied] = useState<string | null>(null)
  useEffect(() => {
    if (!copied) return
    const t = window.setTimeout(() => setCopied(null), 2000)
    return () => window.clearTimeout(t)
  }, [copied])
  const run = (key: string, action: () => Promise<void>) => {
    action().then(() => setCopied(key)).catch(() => setCopied(null))
  }
  return [copied, run]
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <p className="mb-1.5 text-xs font-medium uppercase tracking-wider text-muted">{label}</p>
      {children}
    </div>
  )
}

export default function DigestPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = readFilters(searchParams)
  const rawLimit = Number(searchParams.get('limit'))
  const limit = LIMITS.includes(rawLimit) ? rawLimit : DEFAULT_LIMIT
  const [format, setFormat] = useState<Format>('outlook')
  const [copied, copy] = useCopied()
  const { version } = useRefresh()

  const meta = useFetch<Meta>('/api/meta')
  const query = toApiParams(filters)
  query.set('limit', String(limit))
  const digest = useFetch<Digest>(`/api/digest?${query}`, [version])
  const d = digest.data

  const update = (patch: Partial<Filters>) =>
    setSearchParams(writeFilters({ ...filters, ...patch }, searchParams), { replace: true })
  const setLimit = (n: number) => {
    const next = new URLSearchParams(searchParams)
    if (n === DEFAULT_LIMIT) next.delete('limit')
    else next.set('limit', String(n))
    setSearchParams(next, { replace: true })
  }

  const feedParams = new URLSearchParams(searchParams)
  feedParams.delete('limit')
  const stamp = new Date().toISOString().slice(0, 10).replaceAll('-', '')

  return (
    <>
      <PageHeader
        title="Digest"
        description="Turn a filtered slice of the feed into an email, Teams post or plain-text summary."
        actions={
          <Link to={`/${feedParams.toString() ? `?${feedParams}` : ''}`} className={buttonClasses('secondary')}>
            <ArrowLeft className="h-4 w-4" />
            Back to feed
          </Link>
        }
      />

      <div className="grid items-start gap-6 lg:grid-cols-[320px_1fr]">
        <Card className="space-y-5 p-4 lg:sticky lg:top-24">
          <Field label="Date range">
            <Segmented
              label="Date range"
              value={filters.days}
              onChange={(days) => update({ days })}
              options={DAY_OPTIONS.map((o) => ({ label: o.short, value: o.value, title: o.label }))}
            />
          </Field>
          <Field label="Content type">
            <Segmented label="Content type" value={filters.type} onChange={(type) => update({ type })} options={TYPE_OPTIONS} />
          </Field>
          <Field label="Categories">
            <div className="flex flex-wrap gap-1.5">
              {(meta.data?.categories ?? []).map((c) => (
                <Chip key={c} active={filters.categories.includes(c)} onClick={() => update({ categories: toggle(filters.categories, c) })}>
                  {c}
                </Chip>
              ))}
            </div>
          </Field>
          <Field label="Platforms">
            <PlatformPicker
              platforms={meta.data?.platforms ?? []}
              selected={filters.platforms}
              onChange={(platforms) => update({ platforms })}
            />
          </Field>
          {filters.q && (
            <Field label="Search">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-accent-soft px-3 py-1 text-sm text-accent">
                <Search className="h-3.5 w-3.5" />
                {filters.q}
                <button type="button" aria-label="Remove search" onClick={() => update({ q: '' })}>
                  <X className="h-3.5 w-3.5" />
                </button>
              </span>
            </Field>
          )}
          <Field label="Max articles">
            <Segmented
              label="Max articles"
              value={limit}
              onChange={setLimit}
              options={LIMITS.map((n) => ({ label: String(n), value: n }))}
            />
          </Field>
          {d && (
            <p className="border-t border-border pt-4 text-sm text-muted">
              Including the {plural(d.count, 'newest article')} of {d.total.toLocaleString()} matching.
            </p>
          )}
        </Card>

        <Card className="min-w-0 overflow-hidden">
          {digest.error ? (
            <EmptyState icon={<AlertCircle className="h-5 w-5" />} title="Couldn't build the digest">
              {digest.error}. Is the API server running on port 8000?
            </EmptyState>
          ) : !d ? (
            <div className="space-y-3 p-5">
              <Skeleton className="h-5 w-2/3" />
              <Skeleton className="h-[480px] w-full rounded-lg" />
            </div>
          ) : d.count === 0 ? (
            <EmptyState icon={<Inbox className="h-5 w-5" />} title="Nothing to send yet">
              No articles match these settings. Try a wider date range or fewer filters.
            </EmptyState>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-3 border-b border-border px-4 py-3 sm:px-5">
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium uppercase tracking-wider text-muted">Subject</p>
                  <p className="truncate font-medium" title={d.subject}>{d.subject}</p>
                </div>
                <Button size="sm" onClick={() => copy('subject', () => navigator.clipboard.writeText(d.subject))}>
                  {copied === 'subject' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                  {copied === 'subject' ? 'Copied' : 'Copy subject'}
                </Button>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-5">
                <Segmented
                  label="Format"
                  value={format}
                  onChange={setFormat}
                  options={[
                    { label: 'Outlook', value: 'outlook' },
                    { label: 'Teams', value: 'teams' },
                    { label: 'Plain text', value: 'text' },
                  ]}
                />
                <div className="flex gap-2">
                  {format === 'outlook' && (
                    <>
                      <Button size="sm" variant="primary" onClick={() => copy('outlook', () => copyRichText(d.html, d.text))}>
                        {copied === 'outlook' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                        {copied === 'outlook' ? 'Copied — paste into Outlook' : 'Copy for Outlook'}
                      </Button>
                      <Button size="sm" onClick={() => download(`maintain_${stamp}.html`, d.html, 'text/html')}>
                        <Download className="h-4 w-4" /> .html
                      </Button>
                    </>
                  )}
                  {format === 'teams' && (
                    <Button size="sm" variant="primary" onClick={() => copy('teams', () => navigator.clipboard.writeText(d.teams))}>
                      {copied === 'teams' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                      {copied === 'teams' ? 'Copied — paste into Teams' : 'Copy for Teams'}
                    </Button>
                  )}
                  {format === 'text' && (
                    <>
                      <Button size="sm" variant="primary" onClick={() => copy('text', () => navigator.clipboard.writeText(d.text))}>
                        {copied === 'text' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                        {copied === 'text' ? 'Copied' : 'Copy text'}
                      </Button>
                      <Button size="sm" onClick={() => download(`maintain_${stamp}.txt`, d.text, 'text/plain')}>
                        <Download className="h-4 w-4" /> .txt
                      </Button>
                    </>
                  )}
                </div>
              </div>

              <div className="px-4 pb-4 sm:px-5 sm:pb-5">
                {format === 'outlook' ? (
                  <iframe
                    title="Outlook email preview"
                    sandbox=""
                    srcDoc={d.html}
                    className="h-[640px] w-full rounded-lg border border-border bg-white"
                  />
                ) : (
                  <pre className="max-h-[640px] overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-bg p-4 font-mono text-[13px] leading-relaxed text-fg/90">
                    {format === 'teams' ? d.teams : d.text}
                  </pre>
                )}
              </div>
            </>
          )}
        </Card>
      </div>
    </>
  )
}
