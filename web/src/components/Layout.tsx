import { Moon, RefreshCw, Sun } from 'lucide-react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { parseDate, relativeTime } from '../lib/format'
import { useRefresh } from '../lib/refresh'
import { useTheme } from '../lib/theme'
import { Button, cn } from './ui'

const NAV = [
  { to: '/', label: 'Feed', end: true },
  { to: '/benchmarks', label: 'AI Benchmarks', short: 'Benchmarks', end: false },
  { to: '/digest', label: 'Digest', end: false },
]

function RefreshControl() {
  const { status, trigger } = useRefresh()
  const running = status?.running ?? false
  const updated = relativeTime(parseDate(status?.last_refreshed))

  return (
    <div className="flex items-center gap-2 max-[359px]:hidden">
      <span className="hidden text-sm text-muted md:inline" aria-live="polite">
        {running ? `Refreshing ${status!.done}/${status!.total}` : updated && `Updated ${updated}`}
      </span>
      <Button
        variant="ghost"
        size="icon"
        onClick={trigger}
        disabled={running}
        title={running ? `Refreshing feeds (${status!.done}/${status!.total})` : 'Refresh all feeds'}
        aria-label="Refresh all feeds"
        className="h-9 w-9 sm:h-10 sm:w-10"
      >
        <RefreshCw className={cn('h-[18px] w-[18px]', running && 'animate-spin')} />
      </Button>
    </div>
  )
}

function ThemeToggle() {
  const [theme, toggle] = useTheme()
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggle}
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      className="h-9 w-9 sm:h-10 sm:w-10"
    >
      {theme === 'dark' ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
    </Button>
  )
}

export function Layout() {
  const { status } = useRefresh()
  const progress = status?.running && status.total ? (status.done / status.total) * 100 : null

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-border bg-bg/80 backdrop-blur-md">
        <div className="mx-auto flex h-18 max-w-6xl items-center gap-3 px-4 max-[359px]:gap-2 max-[359px]:px-3 sm:gap-8 sm:px-6">
          <Link to="/" aria-label="m[AI]ntain home" className="flex items-center gap-3 font-semibold tracking-tight">
            <span className="grid h-9 min-w-9 place-items-center rounded-xl bg-accent px-1.5 text-xs font-bold text-accent-fg">
              [AI]
            </span>
            <span className="hidden text-lg sm:inline">
              m<span className="bg-gradient-to-r from-accent to-accent-2 bg-clip-text text-transparent">[AI]</span>ntain
            </span>
          </Link>
          <nav className="flex items-center gap-0.5 sm:gap-1.5">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    'whitespace-nowrap rounded-lg px-2 py-2 text-sm font-medium transition-colors sm:px-3.5 sm:text-[15px]',
                    isActive ? 'bg-surface-2 text-fg' : 'text-muted hover:text-fg',
                  )
                }
              >
                {item.short ? (
                  <>
                    <span className="sm:hidden">{item.short}</span>
                    <span className="hidden sm:inline">{item.label}</span>
                  </>
                ) : (
                  item.label
                )}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-1">
            <RefreshControl />
            <ThemeToggle />
          </div>
        </div>
        {progress !== null && (
          <div className="absolute inset-x-0 bottom-0 h-0.5">
            <div className="h-full bg-accent transition-[width] duration-500" style={{ width: `${progress}%` }} />
          </div>
        )}
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <Outlet />
      </main>
    </div>
  )
}
