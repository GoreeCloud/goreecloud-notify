import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page, type Route } from '@playwright/test'

type Severity = 'info' | 'normal' | 'warning' | 'error' | 'critical'

type Delivery = {
  id: number
  notification_id: number
  source: string
  channel: string
  title: string
  body: string
  severity: Severity
  notification_created_at: string
  delivered_at: string
  expires_at: null
  read_at: string | null
  acknowledged_at: string | null
}

type Subscription = {
  channel_id: number
  channel: string
  name: string
  description: string
  subscribed: boolean
}

const timestamp = '2026-08-14T16:00:00Z'

function delivery(id: number, overrides: Partial<Delivery> = {}): Delivery {
  return {
    id,
    notification_id: id + 1_000,
    source: 'healthchecks',
    channel: 'goreecloud-healthchecks',
    title: `Notification ${id}`,
    body: `Synthetic browser validation notification ${id}`,
    severity: 'normal',
    notification_created_at: timestamp,
    delivered_at: timestamp,
    expires_at: null,
    read_at: null,
    acknowledged_at: null,
    ...overrides,
  }
}

function json(route: Route, body: unknown, status = 200, headers: Record<string, string> = {}) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
    headers,
  })
}

async function mockHealthAndMeta(page: Page) {
  await page.route('**/healthz', (route) => json(route, {
    status: 'ok',
    service: 'GoreeCloud Notify',
    version: '0.1.0-dev',
  }))
}

async function mockAuthenticatedApi(page: Page) {
  const defaultDeliveries = Array.from({ length: 50 }, (_, index) => {
    const id = 150 - index
    return delivery(id, {
      source: index % 2 === 0 ? 'healthchecks' : 'netbird',
      channel: index % 2 === 0 ? 'goreecloud-healthchecks' : 'netbird-alerts',
      title: index === 0 ? 'Backup completed' : `Notification ${id}`,
      severity: index === 3 ? 'warning' : 'normal',
      read_at: index % 4 === 0 ? timestamp : null,
    })
  })
  const liveDelivery = delivery(501, {
    source: 'healthchecks',
    title: 'Live delivery arrived',
    body: 'Synthetic SSE delivery used for browser reconnect validation.',
    severity: 'warning',
  })
  const criticalDelivery = delivery(500, {
    source: 'netbird',
    channel: 'netbird-alerts',
    title: 'Critical network alert',
    body: 'A synthetic critical alert used for browser search validation.',
    severity: 'critical',
  })
  const olderDelivery = delivery(50, {
    title: 'Older notification',
    source: 'healthchecks',
  })

  let subscriptions: Subscription[] = [
    {
      channel_id: 1,
      channel: 'goreecloud-healthchecks',
      name: 'Healthchecks',
      description: 'Healthchecks alerts',
      subscribed: true,
    },
    {
      channel_id: 2,
      channel: 'netbird-alerts',
      name: 'NetBird',
      description: 'NetBird alerts',
      subscribed: false,
    },
  ]
  let streamDelivered = false

  const inboxQueries: string[] = []
  const subscriptionMethods: string[] = []
  const streamRequests: string[] = []

  await mockHealthAndMeta(page)
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname

    if (path === '/api/v1/meta') {
      return json(route, {
        service: 'GoreeCloud Notify',
        version: '0.1.0-dev',
        milestone: 1,
        development_milestone: 4,
        production: false,
        implemented_engine: ['authenticated SSE inbox stream'],
        next_milestone: 'Real-Time Delivery',
        next_slice: 'Milestone 4 reconnect and unread counter refinement',
      })
    }

    if (path === '/api/v1/me') {
      return json(route, {
        id: 1,
        username: 'browser-test',
        display_name: 'Browser Test',
        is_active: true,
        is_admin: true,
      })
    }

    if (path === '/api/v1/csrf') {
      return json(route, { csrf_token: 'synthetic-csrf-token' })
    }

    if (path === '/api/v1/inbox/stream') {
      const lastEventId = request.headers()['last-event-id'] ?? ''
      streamRequests.push(lastEventId)
      const replay = lastEventId === String(liveDelivery.id)
      streamDelivered = true
      return route.fulfill({
        status: 200,
        headers: {
          'content-type': 'text/event-stream',
          'cache-control': 'no-store',
        },
        body: replay
          ? [
              'retry: 3000',
              'event: ready',
              `data: {"cursor":${liveDelivery.id}}`,
              '',
              '',
            ].join('\n')
          : [
              'retry: 3000',
              'event: ready',
              'data: {"cursor":150}',
              '',
              `id: ${liveDelivery.id}`,
              'event: inbox',
              `data: ${JSON.stringify(liveDelivery)}`,
              '',
              '',
            ].join('\n'),
      })
    }

    if (path === '/api/v1/inbox' && request.method() === 'GET') {
      inboxQueries.push(url.search)
      const query = url.searchParams.get('q')?.toLowerCase()
      if (query === 'critical') return json(route, [criticalDelivery])
      if (url.searchParams.has('before_id')) return json(route, [olderDelivery])

      let result = streamDelivered ? [liveDelivery, ...defaultDeliveries].slice(0, 50) : [...defaultDeliveries]
      const read = url.searchParams.get('read')
      if (read === 'false') result = result.filter((item) => item.read_at === null)
      if (read === 'true') result = result.filter((item) => item.read_at !== null)
      const severity = url.searchParams.get('severity')
      if (severity) result = result.filter((item) => item.severity === severity)
      const source = url.searchParams.get('source')
      if (source) result = result.filter((item) => item.source === source)
      return json(route, result)
    }

    const readMatch = path.match(/^\/api\/v1\/inbox\/(\d+)\/read$/)
    if (readMatch) {
      const id = Number(readMatch[1])
      const existing = defaultDeliveries.find((item) => item.id === id) ?? (id === liveDelivery.id ? liveDelivery : criticalDelivery)
      return json(route, {
        ...existing,
        read_at: request.method() === 'DELETE' ? null : timestamp,
      })
    }

    const acknowledgeMatch = path.match(/^\/api\/v1\/inbox\/(\d+)\/acknowledge$/)
    if (acknowledgeMatch) {
      const id = Number(acknowledgeMatch[1])
      const existing = defaultDeliveries.find((item) => item.id === id) ?? (id === liveDelivery.id ? liveDelivery : criticalDelivery)
      return json(route, {
        ...existing,
        read_at: timestamp,
        acknowledged_at: timestamp,
      })
    }

    if (path === '/api/v1/subscriptions' && request.method() === 'GET') {
      return json(route, subscriptions)
    }

    const subscriptionMatch = path.match(/^\/api\/v1\/subscriptions\/(.+)$/)
    if (subscriptionMatch) {
      if (request.headers()['x-csrf-token'] !== 'synthetic-csrf-token') {
        return json(route, { detail: 'CSRF validation failed' }, 403)
      }
      subscriptionMethods.push(request.method())
      const channel = decodeURIComponent(subscriptionMatch[1])
      subscriptions = subscriptions.map((item) => item.channel === channel
        ? { ...item, subscribed: request.method() === 'PUT' }
        : item)
      const updated = subscriptions.find((item) => item.channel === channel)
      return json(route, updated ?? { detail: 'channel not found' }, updated ? 200 : 404)
    }

    if (path === '/api/v1/session' && request.method() === 'DELETE') {
      return route.fulfill({ status: 204 })
    }

    return json(route, { detail: `Unhandled browser test route: ${request.method()} ${path}` }, 500)
  })

  return { inboxQueries, subscriptionMethods, streamRequests }
}

async function assertNoAutomatedWcagViolations(page: Page) {
  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()
  expect(result.violations, JSON.stringify(result.violations, null, 2)).toEqual([])
}

test('authenticated Glaze inbox supports realtime browser interactions and automated accessibility checks', async ({ page }) => {
  const evidence = await mockAuthenticatedApi(page)
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Good day, Browser' })).toBeVisible()
  const inboxNavigation = page.getByRole('navigation', { name: 'Inbox views' })
  await expect(inboxNavigation).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Backup completed' })).toBeVisible()
  await expect(page.getByRole('button', { name: /Live delivery arrived/ })).toBeVisible()
  await expect(page.getByText(/Live updates (connected|reconnecting)/)).toBeVisible()
  await expect.poll(() => evidence.streamRequests.length).toBeGreaterThan(0)
  await expect.poll(
    () => evidence.streamRequests.includes('501'),
    { timeout: 8_000 },
  ).toBe(true)

  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Skip to notifications' })).toBeFocused()

  await inboxNavigation.getByRole('button', { name: /^Unread/ }).click()
  await expect.poll(() => evidence.inboxQueries.some((query) => query.includes('read=false'))).toBe(true)

  await page.getByRole('searchbox', { name: 'Search notifications' }).fill('critical')
  await expect(page.getByRole('heading', { name: 'Critical network alert' })).toBeVisible()
  await expect.poll(() => evidence.inboxQueries.some((query) => query.includes('q=critical'))).toBe(true)

  await page.getByRole('button', { name: 'Clear filters' }).click()
  await expect(page.getByRole('button', { name: /Live delivery arrived/ })).toBeVisible()
  await page.getByRole('button', { name: 'Load more' }).click()
  await expect(page.getByText('Older notification')).toBeVisible()
  await expect.poll(() => evidence.inboxQueries.some((query) => query.includes('before_id='))).toBe(true)

  await page.getByText('Notification channels').click()
  await expect(page.getByText('Unsubscribing does not delete existing notification history.')).toBeVisible()
  const subscribeNetBird = page.getByRole('button', { name: 'Subscribe to NetBird' })
  await expect(subscribeNetBird).toBeVisible()
  await subscribeNetBird.click()
  await expect(page.getByRole('button', { name: 'Unsubscribe from NetBird' })).toBeVisible()
  expect(evidence.subscriptionMethods).toContain('PUT')

  await page.getByRole('button', { name: 'Dark' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')

  await assertNoAutomatedWcagViolations(page)

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByRole('heading', { name: 'Good day, Browser' })).toBeVisible()
  const hasHorizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
  expect(hasHorizontalOverflow).toBe(false)
})

test('sign-in screen has labeled controls and no automated WCAG A/AA violations', async ({ page }) => {
  await mockHealthAndMeta(page)
  await page.route('**/api/v1/meta', (route) => json(route, {
    service: 'GoreeCloud Notify',
    version: '0.1.0-dev',
    milestone: 1,
    development_milestone: 4,
    production: false,
    implemented_engine: ['authenticated SSE inbox stream'],
    next_milestone: 'Real-Time Delivery',
    next_slice: 'Milestone 4 reconnect and unread counter refinement',
  }))
  await page.route('**/api/v1/me', (route) => json(route, { detail: 'authentication required' }, 401))

  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
  await expect(page.getByRole('textbox', { name: 'Username' })).toBeVisible()
  await expect(page.getByLabel('Password')).toHaveAttribute('type', 'password')
  await expect(page.getByRole('button', { name: 'Sign in to Notify' })).toBeVisible()
  await assertNoAutomatedWcagViolations(page)
})
