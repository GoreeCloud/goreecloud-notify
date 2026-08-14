import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import SubscriptionsPanel from './SubscriptionsPanel'
import useInboxStream, {
  type RealtimeDelivery,
  type RealtimeInboxState,
} from './useInboxStream'
import './refinement.css'

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
type InboxDelivery = RealtimeDelivery
type InboxState = RealtimeInboxState

type CsrfToken = {
  csrf_token: string
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''
const csrfHeader = 'X-CSRF-Token'
const inboxPageSize = 50

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
      // Preserve the status-based message for an intentionally empty or non-JSON error response.
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

function buildInboxPath(options: {
  readFilter: ReadFilter
  severityFilter: Severity | 'all'
  sourceFilter: string
  search: string
  beforeId?: number
}): string {
  const params = new URLSearchParams({ limit: String(inboxPageSize) })
  if (options.readFilter === 'read') params.set('read', 'true')
  if (options.readFilter === 'unread') params.set('read', 'false')
  if (options.severityFilter !== 'all') params.set('severity', options.severityFilter)
  if (options.sourceFilter !== 'all') params.set('source', options.sourceFilter)
  if (options.search.trim()) params.set('q', options.search.trim())
  if (options.beforeId !== undefined) params.set('before_id', String(options.beforeId))
  return `/api/v1/inbox?${params.toString()}`
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [meta, setMeta] = useState<ApiMeta | null>(null)
  const [healthError, setHealthError] = useState(false)
  const [user, setUser] = useState<User | null>(null)
  const [sessionLoading, setSessionLoading] = useState(true)
  const [csrfToken, setCsrfToken] = useState<string | null>(null)
  const [deliveries, setDeliveries] = useState<InboxDelivery[]>([])
  const [inboxState, setInboxState] = useState<InboxState | null>(null)
  const [streamCursor, setStreamCursor] = useState<number | null>(null)
  const [knownSources, setKnownSources] = useState<string[]>([])
  const [inboxLoading, setInboxLoading] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [inboxError, setInboxError] = useState<string | null>(null)
  const [loginError, setLoginError] = useState<string | null>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loginBusy, setLoginBusy] = useState(false)
  const [logoutBusy, setLogoutBusy] = useState(false)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [readFilter, setReadFilter] = useState<ReadFilter>('all')
  const [severityFilter, setSeverityFilter] = useState<Severity | 'all'>('all')
  const [sourceFilter, setSourceFilter] = useState('all')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [mutationId, setMutationId] = useState<number | null>(null)
  const [theme, setTheme] = useState<ThemeMode>(initialTheme)
  const [realtimeRefresh, setRealtimeRefresh] = useState(0)

  const handleUnauthorized = useCallback(() => {
    setUser(null)
    setCsrfToken(null)
    setDeliveries([])
    setInboxState(null)
    setStreamCursor(null)
    setKnownSources([])
    setSelectedId(null)
    setHasMore(false)
    setInboxError(null)
  }, [])

  async function loadCsrf() {
    const { data } = await apiRequest<CsrfToken>('/api/v1/csrf')
    setCsrfToken(data.csrf_token)
    return data.csrf_token
  }

  function rememberSources(items: InboxDelivery[]) {
    setKnownSources((current) => Array.from(new Set([...current, ...items.map((item) => item.source)])).sort())
  }

  function applyPage(items: InboxDelivery[], append: boolean) {
    rememberSources(items)
    setHasMore(items.length === inboxPageSize)
    setDeliveries((current) => append ? [...current, ...items] : items)
    setSelectedId((current) => {
      const available = append ? [...deliveries, ...items] : items
      if (current !== null && available.some((delivery) => delivery.id === current)) return current
      return available[0]?.id ?? null
    })
  }

  const refreshAfterStreamHandshake = useCallback((state: InboxState) => {
    setInboxState(state)
    setRealtimeRefresh((current) => current + 1)
  }, [])

  const handleRealtimeState = useCallback((state: InboxState) => {
    setInboxState(state)
    setRealtimeRefresh((current) => current + 1)
  }, [])

  const handleRealtimeDelivery = useCallback((delivery: InboxDelivery) => {
    setKnownSources((current) => Array.from(new Set([...current, delivery.source])).sort())

    if (debouncedSearch.trim()) {
      setRealtimeRefresh((current) => current + 1)
      return
    }
    if (readFilter === 'read') return
    if (severityFilter !== 'all' && delivery.severity !== severityFilter) return
    if (sourceFilter !== 'all' && delivery.source !== sourceFilter) return

    setDeliveries((current) => [delivery, ...current.filter((item) => item.id !== delivery.id)])
    setSelectedId((current) => current ?? delivery.id)
  }, [debouncedSearch, readFilter, severityFilter, sourceFilter])

  const streamState = useInboxStream({
    enabled: Boolean(user && streamCursor !== null),
    initialCursor: streamCursor,
    onReady: refreshAfterStreamHandshake,
    onState: handleRealtimeState,
    onDelivery: handleRealtimeDelivery,
  })

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
      .then(({ data }) => setUser(data))
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return
      })
      .finally(() => setSessionLoading(false))

    return () => controller.abort()
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 250)
    return () => window.clearTimeout(timer)
  }, [search])

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    window.localStorage.setItem('goreecloud-notify-theme', theme)
  }, [theme])

  useEffect(() => {
    if (!user || csrfToken) return
    void loadCsrf().catch((reason: unknown) => {
      if (reason instanceof ApiError && reason.status === 401) {
        handleUnauthorized()
        return
      }
      setInboxError(reason instanceof Error ? reason.message : 'Unable to prepare protected actions')
    })
  }, [user, csrfToken, handleUnauthorized])

  useEffect(() => {
    if (!user) return
    const controller = new AbortController()

    void apiRequest<InboxState>('/api/v1/inbox/state', { signal: controller.signal })
      .then(({ data }) => {
        setInboxState(data)
        setStreamCursor((current) => current ?? data.latest_delivery_id)
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return
        if (reason instanceof ApiError && reason.status === 401) {
          handleUnauthorized()
          return
        }
        setInboxError(reason instanceof Error ? reason.message : 'Unable to synchronize inbox state')
      })

    return () => controller.abort()
  }, [user, handleUnauthorized])

  useEffect(() => {
    if (!user) return
    const controller = new AbortController()
    setInboxLoading(true)
    setInboxError(null)
    const path = buildInboxPath({ readFilter, severityFilter, sourceFilter, search: debouncedSearch })

    void apiRequest<InboxDelivery[]>(path, { signal: controller.signal })
      .then(({ data }) => applyPage(data, false))
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return
        if (reason instanceof ApiError && reason.status === 401) {
          handleUnauthorized()
          return
        }
        setInboxError(reason instanceof Error ? reason.message : 'Unable to load inbox')
      })
      .finally(() => {
        if (!controller.signal.aborted) setInboxLoading(false)
      })

    return () => controller.abort()
  }, [user, readFilter, severityFilter, sourceFilter, debouncedSearch, realtimeRefresh, handleUnauthorized])

  useEffect(() => {
    if (!user || streamState !== 'reconnecting') return

    const validateSession = () => {
      void apiRequest<User>('/api/v1/me')
        .catch((reason: unknown) => {
          if (reason instanceof ApiError && reason.status === 401) handleUnauthorized()
        })
    }
    const initialTimer = window.setTimeout(validateSession, 3_000)
    const interval = window.setInterval(validateSession, 10_000)
    return () => {
      window.clearTimeout(initialTimer)
      window.clearInterval(interval)
    }
  }, [user, streamState, handleUnauthorized])

  const selectedDelivery = useMemo(
    () => deliveries.find((delivery) => delivery.id === selectedId) ?? deliveries[0] ?? null,
    [deliveries, selectedId],
  )

  const loadedUnreadCount = deliveries.filter((delivery) => !delivery.read_at).length
  const loadedAcknowledgedCount = deliveries.filter((delivery) => delivery.acknowledged_at).length
  const totalCount = inboxState?.total_count ?? deliveries.length
  const unreadCount = inboxState?.unread_count ?? loadedUnreadCount
  const acknowledgedCount = inboxState?.acknowledged_count ?? loadedAcknowledgedCount
  const readCount = Math.max(totalCount - unreadCount, 0)
  const filtersActive = readFilter !== 'all' || severityFilter !== 'all' || sourceFilter !== 'all' || Boolean(debouncedSearch.trim())
  const streamLabel = streamState === 'live'
    ? 'Live updates connected'
    : streamState === 'offline'
      ? 'Live updates offline; loaded results are stale until network recovery'
      : streamState === 'reconnecting'
        ? 'Live updates reconnecting; loaded results may be stale until recovery'
        : streamState === 'connecting'
          ? 'Connecting live updates'
          : streamCursor === null
            ? 'Preparing synchronized live updates'
            : 'Live updates idle'

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoginBusy(true)
    setLoginError(null)
    try {
      const { data, response } = await apiRequest<User>('/api/v1/session', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      })
      const token = response.headers.get(csrfHeader)
      setUser(data)
      setPassword('')
      if (token) setCsrfToken(token)
      else await loadCsrf()
    } catch (reason) {
      setLoginError(reason instanceof Error ? reason.message : 'Unable to sign in')
    } finally {
      setLoginBusy(false)
    }
  }

  async function handleLogout() {
    setLogoutBusy(true)
    setInboxError(null)
    try {
      const token = csrfToken ?? (await loadCsrf())
      await apiRequest<void>('/api/v1/session', {
        method: 'DELETE',
        headers: { [csrfHeader]: token },
      })
      handleUnauthorized()
    } catch (reason) {
      setInboxError(`Sign out could not be confirmed. Your session remains active in this browser. ${reason instanceof Error ? reason.message : ''}`.trim())
    } finally {
      setLogoutBusy(false)
    }
  }

  async function loadMore() {
    const beforeId = deliveries.at(-1)?.id
    if (beforeId === undefined || loadingMore || !hasMore) return
    setLoadingMore(true)
    setInboxError(null)
    try {
      const path = buildInboxPath({
        readFilter,
        severityFilter,
        sourceFilter,
        search: debouncedSearch,
        beforeId,
      })
      const { data } = await apiRequest<InboxDelivery[]>(path)
      applyPage(data, true)
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 401) {
        handleUnauthorized()
      } else {
        setInboxError(reason instanceof Error ? reason.message : 'Unable to load more notifications')
      }
    } finally {
      setLoadingMore(false)
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
      const { data: state } = await apiRequest<InboxState>('/api/v1/inbox/state')
      setInboxState(state)
      setRealtimeRefresh((current) => current + 1)
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 401) {
        handleUnauthorized()
      } else {
        setInboxError(reason instanceof Error ? reason.message : 'Unable to update notification')
      }
    } finally {
      setMutationId(null)
    }
  }

  function clearFilters() {
    setSearch('')
    setDebouncedSearch('')
    setReadFilter('all')
    setSeverityFilter('all')
    setSourceFilter('all')
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
            <span>Inbox</span><strong>{totalCount}</strong>
          </button>
          <button className={readFilter === 'unread' ? 'active' : ''} onClick={() => setReadFilter('unread')} aria-pressed={readFilter === 'unread'}>
            <span>Unread</span><strong>{unreadCount}</strong>
          </button>
          <button className={readFilter === 'read' ? 'active' : ''} onClick={() => setReadFilter('read')} aria-pressed={readFilter === 'read'}>
            <span>Read</span><strong>{readCount}</strong>
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
          <button className="text-button" disabled={logoutBusy} onClick={() => void handleLogout()}>
            {logoutBusy ? 'Signing out…' : 'Sign out'}
          </button>
        </div>
      </aside>

      <section className="inbox-column" aria-labelledby="inbox-title">
        <header className="inbox-header">
          <div>
            <span className="eyebrow">Milestone 4 · Real-Time Delivery</span>
            <h1 id="inbox-title">Good day, {user.display_name.split(' ')[0]}</h1>
            <p>{unreadCount ? `${unreadCount} unread notification${unreadCount === 1 ? '' : 's'} need your attention.` : 'No unread notifications need your attention.'}</p>
          </div>
          <button className="refresh-button" onClick={clearFilters} disabled={!filtersActive || inboxLoading}>
            Clear filters
          </button>
        </header>

        <section className="summary-grid" aria-label="Inbox summary">
          <article><span>Inbox total</span><strong>{totalCount}</strong><small>{deliveries.length} loaded in the current view</small></article>
          <article><span>Unread</span><strong>{unreadCount}</strong><small>authoritative server count</small></article>
          <article><span>Acknowledged</span><strong>{acknowledgedCount}</strong><small>authoritative server count</small></article>
        </section>

        <SubscriptionsPanel onUnauthorized={handleUnauthorized} />

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
              <option value="all">All known sources</option>
              {knownSources.map((source) => <option key={source} value={source}>{source}</option>)}
            </select>
          </label>
        </section>

        <div className="result-status" role="status" aria-live="polite">
          {inboxLoading ? `Loading notifications… · ${streamLabel}` : `${deliveries.length} notification${deliveries.length === 1 ? '' : 's'} loaded${filtersActive ? ' for the current filters' : ''}. · ${streamLabel}`}
        </div>
        {inboxError ? <div className="error-banner" role="alert">{inboxError}</div> : null}

        <div className="notification-workspace">
          <section id="notification-list" className="notification-list" aria-label="Notifications" aria-busy={inboxLoading}>
            {deliveries.length ? deliveries.map((delivery) => (
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
                <span>{filtersActive ? 'Adjust or clear the current filters.' : 'Your inbox is empty.'}</span>
              </div>
            )}

            {hasMore ? (
              <div className="list-footer">
                <button className="secondary-button" disabled={loadingMore || inboxLoading} onClick={() => void loadMore()}>
                  {loadingMore ? 'Loading more…' : 'Load more'}
                </button>
              </div>
            ) : null}
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
