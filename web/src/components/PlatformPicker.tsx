import { Check, ChevronDown, Layers, Search } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { Platform } from '../lib/api'
import { toggle } from '../lib/filters'
import { Button, cn } from './ui'

export function PlatformPicker({
  platforms,
  selected,
  onChange,
}: {
  platforms: Platform[]
  selected: string[]
  onChange: (next: string[]) => void
}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const root = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onPointer = (e: MouseEvent) => {
      if (root.current && !root.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const visible = platforms.filter((p) => p.name.toLowerCase().includes(query.trim().toLowerCase()))
  const label =
    selected.length === 0 ? 'All platforms' : selected.length === 1 ? selected[0] : `${selected.length} platforms`

  return (
    <div ref={root} className="relative">
      <Button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="listbox"
        className={cn(selected.length > 0 && 'border-accent/40 text-accent')}
      >
        <Layers className="h-4 w-4" />
        <span className="max-w-[10rem] truncate">{label}</span>
        <ChevronDown className="h-4 w-4 opacity-60" />
      </Button>

      {open && (
        <div className="absolute left-0 z-40 mt-2 w-72 rounded-xl border border-border bg-surface p-2 shadow-xl shadow-black/5 sm:left-auto sm:right-0">
          <div className="relative mb-2">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-subtle" />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search platforms"
              className="h-8 w-full rounded-md border border-border bg-bg pl-8 pr-2.5 text-sm outline-none focus:border-accent"
            />
          </div>
          <div role="listbox" aria-multiselectable className="max-h-72 overflow-y-auto">
            {visible.map((p) => {
              const checked = selected.includes(p.name)
              return (
                <button
                  key={p.name}
                  type="button"
                  role="option"
                  aria-selected={checked}
                  onClick={() => onChange(toggle(selected, p.name))}
                  className="flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left text-sm hover:bg-surface-2"
                >
                  <span
                    className={cn(
                      'grid h-4 w-4 shrink-0 place-items-center rounded border',
                      checked ? 'border-accent bg-accent text-accent-fg' : 'border-border',
                    )}
                  >
                    {checked && <Check className="h-3 w-3" strokeWidth={3} />}
                  </span>
                  <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: p.color }} />
                  <span className="flex-1 truncate">{p.name}</span>
                  <span className="text-xs tabular-nums text-subtle">{p.articles.toLocaleString()}</span>
                </button>
              )
            })}
            {visible.length === 0 && <p className="px-2 py-3 text-sm text-muted">No platforms match.</p>}
          </div>
          {selected.length > 0 && (
            <button
              type="button"
              onClick={() => onChange([])}
              className="mt-2 w-full rounded-md border-t border-border pt-2 text-sm text-muted hover:text-fg"
            >
              Clear selection
            </button>
          )}
        </div>
      )}
    </div>
  )
}
