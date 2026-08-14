import { FormEvent, useEffect, useMemo, useState } from 'react'

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

type User = {
  id: number
  username: string
  display_name: string
  is_active: boolean
  is_admin: boolean
}

type Severity = 'info' | 'normal' | 'warning' | 'error' | 'critical'
type ReadFilter = 'all' | 'unread' | 'read'
type ThemeMode = 'system' | 'light' | 'dark'

type InboxDelivery = {
  id: number
  notification_id: number
  source: string
  channel: string
  title: string
  body: string
  severity: Severity
  notification_created_at: string
  delivered_at: string
  expires_at: string | null
  read_at: string | null
  acknowledged_at: string | null
}

type CsrfToken = {
  csrf_token: string
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''
const csrfHeader = 'X-CSRF-Token'

class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<{ data: T; response: Response }> {
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    credentials: 'include',
    headers,
  })

  if (!response.ok) {
    let message = `Request failed with HTTP ${response.status}`
    try {
      const payload = (await response.json()) as { detail?: string }
      if (payload.detail) message = payload.detail
    } catch {
      // Keep the status-based message when the response is intentionally empty or non-JSON.
    }
    throw new ApiError(response.status, message)
  }

  const data = response.status === 204 ? (undefined as T) : ((await response.json()) as T)
  return { data, response }
}

function formatTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function severityLabel(severity: Severity): string {
  return severity === 'normal' ? 'Normal' : severity.charAt(0).toUpperCase() + severity.slice(1)
}

function initialTheme(): ThemeMode {
  const saved = window.localStorage.getItem('goreecloud-notify-theme')
  return saved === 'light' || saved === 'dark' || saved === 'system' ? saved : 'system'
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [meta, setMeta] = useState<ApiMeta | null>(null)
  const [healthError, setHealthError] = useState(false)
  const [user, setUser] = useState<User | null>(null)
  const [sessionLoading, setSessionLoading] = useState(true)
  const [csrfToken, setCsrfToken] = useState<string | null>(null)
  const [deliveries, setDeliveries] = useState<InboxDelivery[]>([])
  const [inboxLoading, setInboxLoading] = useState(false)
  const [inboxError, setInboxError] = useState<string | null>(null)
  const [loginError, setLoginError] = useState<string | null>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loginBusy, setLoginBusy] = useState(false)
  const [search, setSearch] = useState('')
  const [readFilter, setReadFilter] = useState<ReadFilter>('all')
  const [severityFilter, setSeverityFilter] = useState<Severity | 'all'>('all')
  const [sourceFilter, setSourceFilter] = useState('all')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [mutationId, setMutationId] = useState<number | null>(null)
  const [theme, setTheme] = useState<ThemeMode>(initialTheme)

  async function loadInbox() {
    setInboxLoading(true)
    setInboxError(null)
    try {
      const { data } = await apiRequest<InboxDelivery[]>('/api/v1/inbox?limit=100')
      setDeliveries(data)
      setSelectedId((current) => {
        if (current !== null && data.some((delivery) => delivery.id === current)) return current
        return data[0]?.id ?? null
      })
    } catch (reason) {
      setInboxError(reason instanceof Error ? reason.message : 'Unable to load inbox')
    } finally {
      setInboxLoading(false)
    }
  }

  async function loadCsrf() {
    const { data } = await apiRequest<CsrfToken>('/api/v1/csrf')
    setCsrfToken(data.csrf_token)
    return data.csrf_token
  }

  useEffect(() => {
    const controller = new AbortController()

    void apiRequest<Health>('/healthz', { signal: controller.signal })
      .then(({ data }) => setHealth(data))
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return
        setHealthError(true)
      })

    void apiRequest<ApiMeta>('/api/v1/meta', { signal: controller.signal })
      .then(({ data }) => setMeta(data))
      .catch(() => undefined)

    void apiRequest<User>('/api/v1/me', { signal: controller.signal })
      .then(async ({ data }) => {
        setUser(data)
        setSessionLoading(false)
        await Promise.all([loadCsrf(), loadInbox()])
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return
        setSessionLoading(false)
      })

    return () => controller.abort()
  }, [])

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    window.localStorage.setItem('goreecloud-notify-theme', theme)
  }, [theme])

  const sources = useMemo(
    () => Array.from(new Set(deliveries.map((delivery) => delivery.source))).sort(),
    [deliveries],
  )

  const filteredDeliveries = useMemo(() => {
    const term = search.trim().toLowerCase()
    return deliveries.filter((delivery) => {
      if (readFilter === 'read' && !delivery.read_at) return false
      if (readFilter === 'unread' && delivery.read_at) return false
      if (severityFilter !== 'all' && delivery.severity !== severityFilter) return false
      if (sourceFilter !== 'all' && delivery.source !== sourceFilter) return false
      if (!term) return true
      return [delivery.title, delivery.body, delivery.source, delivery.channel, delivery.severity]
        .join(' ')
        .toLowerCase()
        .includes(term)
    })
  }, [deliveries, readFilter, search, severityFilter, sourceFilter])

  const selectedDelivery = useMemo(
    () => filteredDeliveries.find((delivery) => delivery.id === selectedId) ?? filteredDeliveries[0] ?? null,
    [filteredDeliveries, selectedId],
  )

  const unreadCount = deliveries.filter((delivery) => !delivery.read_at).length
  const acknowledgedCount = deliveries.filter((delivery) => delivery.acknowledged_at).length

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoginBusy(true)
    setLoginError(null)
    try {
      const { data, response } = await apiRequest<User>('/api/v1/session', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      })
      setUser(data)
      setPassword('')
      const token = response.headers.get(csrfHeader)
      if (token) setCsrfToken(token)
      else await loadCsrf()
      await loadInbox()
    } catch (reason) {
      setLoginError(reason instanceof Error ? reason.message : 'Unable to sign in')
    } finally {
      setLoginBusy(false)
    }
  }

  async function handleLogout() {
    try {
      const token = csrfToken ?? (await loadCsrf())
      await apiRequest<void>('/api/v1/session', {
        method: 'DELETE',
        headers: { [csrfHeader]: token },
      })
    } finally {
      setUser(null)
      setCsrfToken(null)
      setDeliveries([])
      setSelectedId(null)
      setInboxError(null)
    }
  }

  async function mutateDelivery(delivery: InboxDelivery, action: 'read' | 'unread' | 'acknowledge') {
    setMutationId(delivery.id)
    setInboxError(null)
    try {
      const token = csrfToken ?? (await loadCsrf())
      const method = action === 'unread' ? 'DELETE' : 'POST'
      const suffix = action === 'acknowledge' ? 'acknowledge' : 'read'
      const { data } = await apiRequest<InboxDelivery>(`/api/v1/inbox/${delivery.id}/${suffix}`, {
        method,
        headers: { [csrfHeader]: token },
      })
      setDeliveries((current) => current.map((item) => (item.id === data.id ? data : item)))
    } catch (reason) {
      setInboxError(reason instanceof Error ? reason.message : 'Unable to update notification')
    } finally {
      setMutationId(null)
    }
  }

  if (sessionLoading) {
    return (
      <main className="shell centered-shell">
        <section className="loading-card" role="status" aria-live="polite">
          <span className="brand-mark">G</span>
          <strong>Opening GoreeCloud Notify</strong>
          <span>Checking your private session…</span>
        </section>
      </main>
    )
  }

  if (!user) {
    return (
      <main className="shell sign-in-shell">
        <section className="auth-layout" aria-labelledby="page-title">
          <div className="auth-intro">
            <div className="brand-row">
              <span className="brand-mark">G</span>
              <span>GoreeCloud</span>
            </div>
            <div>
              <span className="eyebrow">Private notification center</span>
              <h1 id="page-title">Notify</h1>
              <p className="lede">
                One calm place for operational and GoreeCloud application notifications, built with the Glaze UI design language.
              </p>
            </div>
            <div className="service-state" role="status" aria-live="polite">
              <span className={`state-dot ${health ? 'online' : healthError ? 'offline' : ''}`} />
              <span>{health ? 'Development backend online' : healthError ? 'Backend unavailable' : 'Checking backend'}</span>
            </div>
          </div>

          <form className="login-card" onSubmit={handleLogin}>
            <div>
              <span className="eyebrow">Human session</span>
              <h2>Sign in</h2>
              <p>Use an administrator-provisioned GoreeCloud Notify account.</p>
            </div>
            <label>
              <span>Username</span>
              <input
                name="username"
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
              />
            </label>
            <label>
              <span>Password</span>
              <input
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>
            {loginError ? <div className="error-banner" role="alert">{loginError}</div> : null}
            <button className="primary-button" type="submit" disabled={loginBusy}>
              {loginBusy ? 'Signing in…' : 'Sign in to Notify'}
            </button>
            <p className="auth-footnote">
              ntfy remains the active production notification service during this development milestone.
            </p>
          </form>
        </section>
      </main>
    )
  }

  return (
    <main className="app-shell">
      <a className="skip-link" href="#notification-list">Skip to notifications</a>
      <aside className="sidebar" aria-label="Notify navigation">
        <div className="sidebar-brand">
          <span className="brand-mark compact">G</span>
          <div>
            <strong>Notify</strong>
            <span>GoreeCloud</span>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label="Inbox views">
          <button className={readFilter === 'all' ? 'active' : ''} onClick={() => setReadFilter('all')} aria-pressed={readFilter === 'all'}>
            <span>Inbox</span><strong>{deliveries.length}</strong>
          </button>
          <button className={readFilter === 'unread' ? 'active' : ''} onClick={() => setReadFilter('unread')} aria-pressed={readFilter === 'unread'}>
            <span>Unread</span><strong>{unreadCount}</strong>
          </button>
          <button className={readFilter === 'read' ? 'active' : ''} onClick={() => setReadFilter('read')} aria-pressed={readFilter === 'read'}>
            <span>Read</span><strong>{deliveries.length - unreadCount}</strong>
          </button>
        </nav>

        <div className="sidebar-spacer" />

        <div className="theme-control" aria-label="Appearance">
          <span>Appearance</span>
          <div className="segmented-control compact-control">
            {(['system', 'light', 'dark'] as ThemeMode[]).map((mode) => (
              <button key={mode} onClick={() => setTheme(mode)} aria-pressed={theme === mode} className={theme === mode ? 'active' : ''}>
                {mode === 'system' ? 'Auto' : mode === 'light' ? 'Light' : 'Dark'}
              </button>
            ))}
          </div>
        </div>

        <div className="profile-card">
          <div className="avatar" aria-hidden="true">{user.display_name.charAt(0).toUpperCase()}</div>
          <div className="profile-copy">
            <strong>{user.display_name}</strong>
            <span>@{user.username}{user.is_admin ? ' · Admin' : ''}</span>
          </div>
          <button className="text-button" onClick={() => void handleLogout()}>Sign out</button>
        </div>
      </aside>

      <section className="inbox-column" aria-labelledby="inbox-title">
        <header className="inbox-header">
          <div>
            <span className="eyebrow">Milestone 3 · Glaze UI Inbox</span>
            <h1 id="inbox-title">Good day, {user.display_name.split(' ')[0]}</h1>
            <p>{unreadCount ? `${unreadCount} unread notification${unreadCount === 1 ? '' : 's'} need your attention.` : 'You are caught up.'}</p>
          </div>
          <button className="refresh-button" onClick={() => void loadInbox()} disabled={inboxLoading}>
            {inboxLoading ? 'Refreshing…' : 'Refresh'}
          </button>
        </header>

        <section className="summary-grid" aria-label="Inbox summary">
          <article><span>Loaded</span><strong>{deliveries.length}</strong><small>most recent deliveries</small></article>
          <article><span>Unread</span><strong>{unreadCount}</strong><small>waiting to be reviewed</small></article>
          <article><span>Acknowledged</span><strong>{acknowledgedCount}</strong><small>explicitly handled</small></article>
        </section>

        <section className="toolbar" aria-label="Notification filters">
          <label className="search-field">
            <span className="visually-hidden">Search notifications</span>
            <input
              type="search"
              placeholder="Search title, body, source, or channel"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <label>
            <span className="visually-hidden">Severity</span>
            <select value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value as Severity | 'all')}>
              <option value="all">All severities</option>
              <option value="critical">Critical</option>
              <option value="error">Error</option>
              <option value="warning">Warning</option>
              <option value="normal">Normal</option>
              <option value="info">Info</option>
            </select>
          </label>
          <label>
            <span className="visually-hidden">Source</span>
            <select value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)}>
              <option value="all">All sources</option>
              {sources.map((source) => <option key={source} value={source}>{source}</option>)}
            </select>
          </label>
        </section>

        {inboxError ? <div className="error-banner" role="alert">{inboxError}</div> : null}

        <div className="notification-workspace">
          <section id="notification-list" className="notification-list" aria-label="Notifications" aria-busy={inboxLoading}>
            {filteredDeliveries.length ? filteredDeliveries.map((delivery) => (
              <button
                key={delivery.id}
                className={`notification-row ${selectedDelivery?.id === delivery.id ? 'selected' : ''} ${delivery.read_at ? 'read' : 'unread'}`}
                onClick={() => setSelectedId(delivery.id)}
                aria-pressed={selectedDelivery?.id === delivery.id}
              >
                <span className={`source-orb severity-${delivery.severity}`} aria-hidden="true">{delivery.source.charAt(0).toUpperCase()}</span>
                <span className="notification-copy">
                  <span className="notification-meta">
                    <span>{delivery.source}</span>
                    <time dateTime={delivery.notification_created_at}>{formatTime(delivery.notification_created_at)}</time>
                  </span>
                  <strong>{delivery.title}</strong>
                  <span className="body-preview">{delivery.body}</span>
                  <span className="notification-tags">
                    <span className={`severity-badge severity-${delivery.severity}`}>{severityLabel(delivery.severity)}</span>
                    <span>#{delivery.channel}</span>
                    {delivery.acknowledged_at ? <span>Acknowledged</span> : null}
                  </span>
                </span>
                {!delivery.read_at ? <span className="unread-dot" aria-label="Unread" /> : null}
              </button>
            )) : (
              <div className="empty-state" role="status">
                <strong>No matching notifications</strong>
                <span>{deliveries.length ? 'Adjust the current filters or search.' : 'Your inbox is empty.'}</span>
              </div>
            )}
          </section>

          <aside className="detail-panel" aria-label="Notification detail">
            {selectedDelivery ? (
              <>
                <div className="detail-head">
                  <div>
                    <span className={`severity-badge severity-${selectedDelivery.severity}`}>{severityLabel(selectedDelivery.severity)}</span>
                    <h2>{selectedDelivery.title}</h2>
                  </div>
                  {!selectedDelivery.read_at ? <span className="unread-label">Unread</span> : null}
                </div>
                <div className="detail-provenance">
                  <div><span>Source</span><strong>{selectedDelivery.source}</strong></div>
                  <div><span>Channel</span><strong>{selectedDelivery.channel}</strong></div>
                  <div><span>Created</span><strong>{formatTime(selectedDelivery.notification_created_at)}</strong></div>
                </div>
                <p className="detail-body">{selectedDelivery.body}</p>
                <div className="detail-actions">
                  <button
                    className="primary-button"
                    disabled={mutationId === selectedDelivery.id || Boolean(selectedDelivery.acknowledged_at)}
                    onClick={() => void mutateDelivery(selectedDelivery, 'acknowledge')}
                  >
                    {selectedDelivery.acknowledged_at ? 'Acknowledged' : 'Acknowledge'}
                  </button>
                  <button
                    className="secondary-button"
                    disabled={mutationId === selectedDelivery.id}
                    onClick={() => void mutateDelivery(selectedDelivery, selectedDelivery.read_at ? 'unread' : 'read')}
                  >
                    {selectedDelivery.read_at ? 'Mark unread' : 'Mark read'}
                  </button>
                </div>
              </>
            ) : (
              <div className="detail-empty">
                <strong>Select a notification</strong>
                <span>Notification detail and state actions appear here.</span>
              </div>
            )}
          </aside>
        </div>

        <footer className="development-footer">
          <span className={`state-dot ${health ? 'online' : healthError ? 'offline' : ''}`} />
          <span>{meta ? `Milestone ${meta.development_milestone} · ${meta.next_milestone} · Next: ${meta.next_slice}` : 'Pre-production GoreeCloud Notify development'}</span>
        </footer>
      </section>
    </main>
  )
}
