import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { getJSON, postJSON, type Status } from './api'

type RefreshContextValue = {
  status?: Status
  /** Bumps each time a background refresh finishes, so pages can re-fetch. */
  version: number
  trigger: () => void
}

const RefreshContext = createContext<RefreshContextValue>({ version: 0, trigger: () => {} })

const IDLE_POLL_MS = 30_000
const ACTIVE_POLL_MS = 1_500

export function RefreshProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>()
  const [version, setVersion] = useState(0)
  const wasRunning = useRef(false)
  const timer = useRef<number | undefined>(undefined)

  const poll = useCallback(async () => {
    window.clearTimeout(timer.current)
    let running = wasRunning.current
    try {
      const s = await getJSON<Status>('/api/status')
      setStatus(s)
      running = s.running
      if (wasRunning.current && !s.running) setVersion((v) => v + 1)
      wasRunning.current = s.running
    } catch {
      // API unreachable — keep polling at the idle rate.
    }
    timer.current = window.setTimeout(poll, running ? ACTIVE_POLL_MS : IDLE_POLL_MS)
  }, [])

  useEffect(() => {
    poll()
    return () => window.clearTimeout(timer.current)
  }, [poll])

  const trigger = useCallback(() => {
    postJSON('/api/refresh')
      .catch(() => {})
      .finally(poll)
  }, [poll])

  return <RefreshContext.Provider value={{ status, version, trigger }}>{children}</RefreshContext.Provider>
}

export function useRefresh(): RefreshContextValue {
  return useContext(RefreshContext)
}
