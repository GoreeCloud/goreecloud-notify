import { useEffect, useState } from 'react'

type Health = {
  status: string
  service: string
  version: string
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    fetch(`${apiBaseUrl}/healthz`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Backend returned HTTP ${response.status}`)
        return response.json() as Promise<Health>
      })
      .then(setHealth)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return
        setError(reason instanceof Error ? reason.message : 'Unable to reach backend')
      })

    return () => controller.abort()
  }, [])

  return (
    <main className="shell">
      <section className="hero" aria-labelledby="page-title">
        <div className="eyebrow">GoreeCloud · Native Application</div>
        <h1 id="page-title">Notify</h1>
        <p className="lede">
          A private notification layer being built for GoreeCloud. Milestone 1 establishes the
          application foundation without changing the active ntfy service.
        </p>

        <div className="status-card" role="status" aria-live="polite">
          <div>
            <span className="status-label">Development state</span>
            <strong>Milestone 1 · Foundation</strong>
          </div>
          <span className={`status-pill ${health ? 'online' : error ? 'offline' : ''}`}>
            {health ? 'Backend online' : error ? 'Backend unavailable' : 'Checking backend'}
          </span>
        </div>

        <div className="grid" aria-label="Foundation capabilities">
          <article className="glass-card">
            <span className="card-kicker">API</span>
            <h2>FastAPI foundation</h2>
            <p>Health, metadata, SQLite persistence, and the first-class GoreeCloud Notify data model.</p>
          </article>
          <article className="glass-card">
            <span className="card-kicker">Interface</span>
            <h2>Glaze UI baseline</h2>
            <p>A responsive, accessible visual foundation for the notification inbox planned in Milestone 3.</p>
          </article>
          <article className="glass-card">
            <span className="card-kicker">Migration</span>
            <h2>ntfy remains active</h2>
            <p>No producer, topic, DNS route, or production notification path changes during this milestone.</p>
          </article>
        </div>
      </section>
    </main>
  )
}
