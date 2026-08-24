import { FormEvent, useEffect, useState } from 'react'
import BrowserNotificationSettings from './BrowserNotificationSettings'
import { useBrowserNotificationsContext } from './BrowserNotificationsContext'
import './subscriptions.css'

type SubscriptionRead = {
  channel_id: number
  channel: string
  name: string
  description: string | null
  subscribed: boolean
}

type ChannelRead = {
  id: number
  slug: string
  name: string
  description: string | null
}

type CsrfResponse = {
  csrf_token: string
}

type SubscriptionsPanelProps = {
  isAdmin: boolean
  onUnauthorized: () => void
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''
const csrfHeader = 'X-CSRF-Token'

class SubscriptionApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
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
      // Keep the status-based fallback when the error response is empty or non-JSON.
    }
    throw new SubscriptionApiError(response.status, message)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export default function SubscriptionsPanel({ isAdmin, onUnauthorized }: SubscriptionsPanelProps) {
  const [subscriptions, setSubscriptions] = useState<SubscriptionRead[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busyChannel, setBusyChannel] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [channelName, setChannelName] = useState('')
  const [channelSlug, setChannelSlug] = useState('')
  const [channelDescription, setChannelDescription] = useState('')
  const browserNotifications = useBrowserNotificationsContext()

  async function loadSubscriptions(signal?: AbortSignal) {
    const items = await request<SubscriptionRead[]>('/api/v1/subscriptions', { signal })
    setSubscriptions(items)
  }

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)

    void loadSubscriptions(controller.signal)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return
        if (reason instanceof SubscriptionApiError && reason.status === 401) {
          onUnauthorized()
          return
        }
        setError(reason instanceof Error ? reason.message : 'Unable to load notification channels')
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })

    return () => controller.abort()
  }, [onUnauthorized])

  async function getCsrfToken(): Promise<string> {
    const response = await request<CsrfResponse>('/api/v1/csrf')
    return response.csrf_token
  }

  async function toggleSubscription(subscription: SubscriptionRead) {
    setBusyChannel(subscription.channel)
    setError(null)
    try {
      const csrfToken = await getCsrfToken()
      const updated = await request<SubscriptionRead>(
        `/api/v1/subscriptions/${encodeURIComponent(subscription.channel)}`,
        {
          method: subscription.subscribed ? 'DELETE' : 'PUT',
          headers: { [csrfHeader]: csrfToken },
        },
      )
      setSubscriptions((current) => current.map((item) => item.channel === updated.channel ? updated : item))
    } catch (reason) {
      if (reason instanceof SubscriptionApiError && reason.status === 401) {
        onUnauthorized()
        return
      }
      setError(reason instanceof Error ? reason.message : 'Unable to update channel subscription')
    } finally {
      setBusyChannel(null)
    }
  }

  async function createChannel(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const name = channelName.trim()
    const slug = channelSlug.trim().toLowerCase()
    if (!name || !slug) {
      setError('Channel name and topic slug are required.')
      return
    }

    setCreating(true)
    setError(null)
    try {
      const csrfToken = await getCsrfToken()
      const created = await request<ChannelRead>('/api/v1/channels', {
        method: 'POST',
        headers: {
          [csrfHeader]: csrfToken,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          slug,
          name,
          description: channelDescription.trim() || null,
        }),
      })
      await request<SubscriptionRead>(`/api/v1/subscriptions/${encodeURIComponent(created.slug)}`, {
        method: 'PUT',
        headers: { [csrfHeader]: csrfToken },
      })
      await loadSubscriptions()
      setChannelName('')
      setChannelSlug('')
      setChannelDescription('')
    } catch (reason) {
      if (reason instanceof SubscriptionApiError && reason.status === 401) {
        onUnauthorized()
        return
      }
      setError(reason instanceof Error ? reason.message : 'Unable to create notification channel')
    } finally {
      setCreating(false)
    }
  }

  const subscribedCount = subscriptions.filter((subscription) => subscription.subscribed).length

  return (
    <div className="notification-preferences-stack">
      <details className="subscriptions-panel">
        <summary>
          <span>
            <strong>Notification channels</strong>
            <small>{loading ? 'Loading channel state…' : `${subscribedCount} of ${subscriptions.length} subscribed`}</small>
          </span>
          <span className="subscriptions-summary-action">Manage</span>
        </summary>

        <div className="subscriptions-content">
          <p className="subscriptions-guidance">
            Choose which channels create future inbox deliveries for this account. Unsubscribing does not delete existing notification history.
          </p>

          {isAdmin ? (
            <form onSubmit={(event) => void createChannel(event)} className="subscription-row">
              <div className="subscription-copy">
                <strong>Add approved topic</strong>
                <label>
                  Name
                  <input value={channelName} onChange={(event) => setChannelName(event.target.value)} maxLength={200} required />
                </label>
                <label>
                  Topic slug
                  <input
                    value={channelSlug}
                    onChange={(event) => setChannelSlug(event.target.value)}
                    pattern="[a-z0-9][a-z0-9._-]{0,119}"
                    placeholder="goreecloud-example"
                    maxLength={120}
                    required
                  />
                </label>
                <label>
                  Description
                  <input value={channelDescription} onChange={(event) => setChannelDescription(event.target.value)} maxLength={2000} />
                </label>
              </div>
              <button type="submit" className="subscription-toggle active" disabled={creating}>
                {creating ? 'Adding…' : 'Add topic'}
              </button>
            </form>
          ) : null}

          {error ? <div className="error-banner" role="alert">{error}</div> : null}

          <div className="subscriptions-list" aria-busy={loading}>
            {loading ? (
              <div className="subscription-placeholder" role="status">Loading notification channels…</div>
            ) : subscriptions.length ? subscriptions.map((subscription) => (
              <div className="subscription-row" key={subscription.channel_id}>
                <div className="subscription-copy">
                  <strong>{subscription.name}</strong>
                  <span>#{subscription.channel}</span>
                  {subscription.description ? <p>{subscription.description}</p> : null}
                </div>
                <button
                  type="button"
                  className={`subscription-toggle ${subscription.subscribed ? 'active' : ''}`}
                  aria-pressed={subscription.subscribed}
                  aria-label={`${subscription.subscribed ? 'Unsubscribe from' : 'Subscribe to'} ${subscription.name}`}
                  disabled={busyChannel === subscription.channel}
                  onClick={() => void toggleSubscription(subscription)}
                >
                  <span aria-hidden="true" />
                  {busyChannel === subscription.channel
                    ? 'Updating…'
                    : subscription.subscribed ? 'Subscribed' : 'Off'}
                </button>
              </div>
            )) : (
              <div className="subscription-placeholder" role="status">No notification channels are currently available.</div>
            )}
          </div>
        </div>
      </details>

      <BrowserNotificationSettings
        permission={browserNotifications.permission}
        enabled={browserNotifications.enabled}
        busy={browserNotifications.busy}
        onEnable={browserNotifications.enable}
        onDisable={browserNotifications.disable}
      />
    </div>
  )
}
