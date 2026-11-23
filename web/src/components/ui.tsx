import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from 'react'
import { readableText } from '../lib/format'

export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ')
}

type Variant = 'primary' | 'secondary' | 'ghost'
type Size = 'sm' | 'md' | 'icon'

export function buttonClasses(variant: Variant = 'secondary', size: Size = 'md', className?: string): string {
  return cn(
    'inline-flex shrink-0 items-center justify-center gap-2 rounded-lg text-sm font-medium transition-colors',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 disabled:pointer-events-none disabled:opacity-50',
    size === 'sm' && 'h-8 px-3',
    size === 'md' && 'h-9 px-3.5',
    size === 'icon' && 'h-9 w-9',
    variant === 'primary' && 'bg-accent text-accent-fg hover:bg-accent/90',
    variant === 'secondary' && 'border border-border bg-surface text-fg hover:bg-surface-2',
    variant === 'ghost' && 'text-muted hover:bg-surface-2 hover:text-fg',
    className,
  )
}

export function Button({
  variant,
  size,
  className,
  type = 'button',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size }) {
  return <button type={type} className={buttonClasses(variant, size, className)} {...props} />
}

export function ExternalLink({ className, ...props }: AnchorHTMLAttributes<HTMLAnchorElement>) {
  return <a target="_blank" rel="noopener noreferrer" className={className} {...props} />
}

export function Segmented<T extends string | number | null>({
  options,
  value,
  onChange,
  label,
}: {
  options: { label: ReactNode; value: T; title?: string }[]
  value: T
  onChange: (value: T) => void
  label: string
}) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="inline-flex max-w-full overflow-x-auto rounded-lg border border-border bg-surface-2 p-0.5 [scrollbar-width:none]"
    >
      {options.map((o) => {
        const active = o.value === value
        return (
          <button
            key={String(o.value)}
            type="button"
            role="radio"
            aria-checked={active}
            title={o.title}
            onClick={() => onChange(o.value)}
            className={cn(
              'h-7 whitespace-nowrap rounded-md px-2.5 text-sm font-medium transition-colors',
              active ? 'bg-surface text-fg shadow-sm' : 'text-muted hover:text-fg',
            )}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}

export function Chip({
  active,
  onClick,
  children,
  color,
}: {
  active: boolean
  onClick: () => void
  children: ReactNode
  color?: string
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        'inline-flex h-7 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border px-3 text-sm font-medium transition-colors',
        active
          ? 'border-accent/40 bg-accent-soft text-accent'
          : 'border-border text-muted hover:bg-surface-2 hover:text-fg',
      )}
    >
      {color && <span className="h-2 w-2 rounded-full" style={{ background: color }} />}
      {children}
    </button>
  )
}

const BADGE_TONES = {
  neutral: 'bg-surface-2 text-muted',
  green: 'bg-lime-500/10 text-lime-700 dark:text-lime-400',
  blue: 'bg-sky-500/10 text-sky-700 dark:text-sky-400',
  amber: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  violet: 'bg-violet-500/10 text-violet-700 dark:text-violet-400',
  red: 'bg-red-500/10 text-red-700 dark:text-red-400',
}

export function Badge({ tone = 'neutral', children }: { tone?: keyof typeof BADGE_TONES; children: ReactNode }) {
  return (
    <span className={cn('inline-flex items-center rounded-md px-1.5 py-0.5 text-xs font-medium', BADGE_TONES[tone])}>
      {children}
    </span>
  )
}

const TYPE_BADGES: Record<string, { tone: keyof typeof BADGE_TONES; label: string }> = {
  releases: { tone: 'green', label: 'Release' },
  video: { tone: 'red', label: 'Video' },
  blog: { tone: 'blue', label: 'Blog' },
}

export function TypeBadge({ type }: { type: string }) {
  const { tone, label } = TYPE_BADGES[type] ?? TYPE_BADGES.blog
  return <Badge tone={tone}>{label}</Badge>
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn('rounded-xl border border-border bg-surface', className)}>{children}</div>
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-md bg-surface-2', className)} />
}

export function EmptyState({
  icon,
  title,
  children,
  action,
}: {
  icon: ReactNode
  title: string
  children?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center px-6 py-16 text-center">
      <div className="mb-4 grid h-12 w-12 place-items-center rounded-full bg-surface-2 text-muted">{icon}</div>
      <h3 className="font-semibold">{title}</h3>
      {children && <p className="mt-1 max-w-sm text-sm text-muted">{children}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function Avatar({ name, color, size = 36 }: { name: string; color: string; size?: number }) {
  return (
    <div
      aria-hidden
      className="grid shrink-0 place-items-center rounded-lg font-semibold"
      style={{ background: color, color: readableText(color), width: size, height: size, fontSize: size * 0.4 }}
    >
      {name.charAt(0).toUpperCase() || '?'}
    </div>
  )
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string
  description?: ReactNode
  actions?: ReactNode
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}
