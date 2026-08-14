import { useEffect, useState } from 'react'

type Health = {
  status: string
  service: string
  version: string
}

type ApiMeta = {
  service: string
  version: string
  milestone: number
  development_milestone: number
  production: boolean
  implemented_engine: string[]
  next_milestone: string
  next_slice: string
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

async function fetchJson<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, { signal })
  if (!response.ok) throw new Error(`Backend returned HTTP ${response.status}`)
  return response.json() as Promise<T>
}

function errorMessage(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [meta, setMeta] = useState<ApiMeta | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)
  const [metaError, setMetaError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    void fetchJson<Health>('/healthz', controller.signal)
      .then(setHealth)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return
        setHealthError(errorMessage(reason, 'Unable to reach backend'))
      })

    void fetchJson<ApiMeta>('/api/v1/meta', controller.signal)
      .then(setMeta)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return
        setMetaError(errorMessage(reason, 'Unable to load development metadata'))
      })

    return () => controller.abort()
  }, [])

  const developmentState = meta
    ? `Milestone ${meta.development_milestone} · ${meta.next_milestone}`
    : metaError
      ? 'Development metadata unavailable'
      : 'Loading development metadata'

  return (
    <main className="shell">
      <section className="hero" aria-labelledby="page-title">
        <div className="eyebrow">GoreeCloud · Native Application</div>
        <h1 id="page-title">Notify</h1>
        <p className="lede">
          A private notification layer being built for GoreeCloud. The current pre-production stack
          is advancing the notification engine while ntfy remains the active production service.
        </p>

        <div className="status-card" role="status" aria-live="polite">
          <div>
            <span className="status-label">Development state</span>
            <strong>{developmentState}</strong>
            <span className="status-detail">
              {meta ? `Next: ${meta.next_slice}` : metaError ?? 'Reading roadmap state from the API'}
            </span>
          </div>
          <span className={`status-pill ${health ? 'online' : healthError ? 'offline' : ''}`}>
            {health ? 'Backend online' : healthError ? 'Backend unavailable' : 'Checking backend'}
          </span>
        </div>

        <div className="grid" aria-label="Current development capabilities">
          <article className="glass-card">
            <span className="card-kicker">Engine</span>
            <h2>Notification engine</h2>
            <p>
              {meta
                ? `${meta.implemented_engine.length} implemented engine capabilities are reported by the current API metadata.`
                : metaError
                  ? 'Development metadata unavailable; engine capability count could not be loaded.'
                  : 'Loading the implemented engine capability count from the backend.'}
            </p>
          </article>
          <article className="glass-card">
            <span className="card-kicker">Security</span>
            <h2>Session-bound controls</h2>
            <p>
              Human sessions, CSRF-protected state changes, producer scopes, and administrator-only
              retention analysis remain separated by authorization boundary.
            </p>
          </article>
          <article className="glass-card">
            <span className="card-kicker">Migration</span>
            <h2>ntfy remains active</h2>
            <p>
              GoreeCloud Notify is still pre-production. No producer, DNS, Caddy, or production
              notification path is cut over by this development stack.
            </p>
          </article>
        </div>
      </section>
    </main>
  )
}
