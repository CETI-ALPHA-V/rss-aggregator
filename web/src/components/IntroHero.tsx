import { ArrowRight, BarChart3, Mail, Newspaper, X } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

function Feature({
  icon,
  title,
  children,
  to,
}: {
  icon: ReactNode
  title: string
  children: ReactNode
  to: string
}) {
  const className =
    'group flex h-full flex-col rounded-xl border border-border bg-bg/60 p-4 transition-colors hover:border-accent/50 hover:bg-accent-soft/40'
  const body = (
    <>
      <span className="mb-3 grid h-9 w-9 place-items-center rounded-lg bg-accent-soft text-accent">{icon}</span>
      <span className="flex items-center gap-1.5 font-medium">
        {title}
        <ArrowRight className="h-3.5 w-3.5 text-subtle transition-transform group-hover:translate-x-0.5 group-hover:text-accent" />
      </span>
      <span className="mt-1 text-sm leading-relaxed text-muted">{children}</span>
    </>
  )
  return to.startsWith('#') ? (
    <a href={to} className={className}>{body}</a>
  ) : (
    <Link to={to} className={className}>{body}</Link>
  )
}

export function IntroHero({ platformCount, onDismiss }: { platformCount?: number; onDismiss: () => void }) {
  return (
    <section
      aria-labelledby="intro-title"
      className="relative mb-10 overflow-hidden rounded-2xl border border-border bg-surface px-5 py-7 sm:px-8 sm:py-9"
    >
      <div aria-hidden className="pointer-events-none absolute -right-20 -top-28 h-72 w-72 rounded-full bg-accent/15 blur-3xl" />
      <div aria-hidden className="pointer-events-none absolute -bottom-36 left-1/4 h-72 w-72 rounded-full bg-accent-2/10 blur-3xl" />

      <button
        type="button"
        onClick={onDismiss}
        aria-label="Hide introduction"
        title="Hide introduction"
        className="absolute right-3 top-3 grid h-8 w-8 place-items-center rounded-lg text-subtle transition-colors hover:bg-surface-2 hover:text-fg"
      >
        <X className="h-4 w-4" />
      </button>

      <div className="relative">
        <p className="text-xs font-semibold uppercase tracking-widest text-accent">AI · Data · Cloud · Marketing</p>
        <h1 id="intro-title" className="mt-3 max-w-2xl text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
          Stay ahead of every release{' '}
          <span className="bg-gradient-to-r from-accent to-accent-2 bg-clip-text text-transparent">your stack ships.</span>
        </h1>
        <p className="mt-4 max-w-2xl text-base leading-relaxed text-muted">
          m[AI]ntain watches the release notes, engineering blogs and official YouTube channels of{' '}
          {platformCount ? `${platformCount} platforms` : 'the platforms'} you build on — AI labs, data tools, clouds and
          ad platforms — and turns them into one feed you can scan in minutes. Know what changed before it breaks a
          pipeline, a model choice or a campaign.
        </p>

        <div className="mt-7 grid gap-3 sm:grid-cols-3">
          <Feature icon={<Newspaper className="h-4 w-4" />} title="Scan the feed" to="#latest">
            Browse by category, company or content type, and search everything at once.
          </Feature>
          <Feature icon={<BarChart3 className="h-4 w-4" />} title="AI benchmarks" to="/benchmarks">
            Benchmark scores, cost per task and head-to-head comparisons of the top LLMs.
          </Feature>
          <Feature icon={<Mail className="h-4 w-4" />} title="Share a digest" to="/digest">
            Turn any filtered view into an Outlook email or Teams post for your team.
          </Feature>
        </div>
      </div>
    </section>
  )
}
