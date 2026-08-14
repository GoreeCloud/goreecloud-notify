import { expect, test, type Page, type Route } from '@playwright/test'

type Delivery = {
  id: number
  notification_id: number
  source: string
  channel: string
  title: string
  body: string
  severity: 'normal' | 'warning'
  notification_created_at: string
  delivered_at: string
  expires_at: null
  read_at: null
  acknowledged_at: null
}

const timestamp = '2026-08-14T18:00:00Z'

function delivery(id: number, title: string): Delivery {
  return {
    id,
    notification_id: id + 1_000,
    source: 'acceptance-source',
    channel: 'acceptance-channel',
    title,
    body: `Synthetic acceptance delivery ${id}`,
    severity: 'normal',
    notification_created_at: timestamp,
    delivered_at: timestamp,
    expires_at: null,
    read_at: null,
    acknowledged_at: null,
  }
}

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

async function mockCommon(page: Page) {
  await page.route('**/healthz', (route) => json(route, {
    status: 'ok',
    service: 'GoreeCloud Notify',
    version: '0.1.0-dev',
  }))
}

async function mockMultiTabApi(page: Page, streamQueries: string[]) {
  const baseDelivery = delivery(200, 'Existing notification')
  const liveDelivery = delivery(201, 'Shared realtime notification')
  let streamOpened = false

  await mockCommon(page)
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
        implemented_engine: ['authenticated SSE inbox stream', 'acceptance stability validation'],
        next_milestone: 'Real-Time Delivery',
        next_slice: 'Milestone 4 acceptance and stabilization',
      })
    }
    if (path === '/api/v1/me') {
      return json(route, {
        id: 1,
        username: 'acceptance-user',
        display_name: 'Acceptance User',
        is_active: true,
        is_admin: false,
      })
    }
    if (path === '/api/v1/csrf') return json(route, { csrf_token: 'synthetic-csrf-token' })
    if (path === '/api/v1/subscriptions') return json(route, [])
    if (path === '/api/v1/inbox/state') {
      return json(route, streamOpened
        ? { latest_delivery_id: 201, total_count: 2, unread_count: 2, acknowledged_count: 0 }
        : { latest_delivery_id: 200, total_count: 1, unread_count: 1, acknowledged_count: 0 })
    }
    if (path === '/api/v1/inbox' && request.method() === 'GET') {
      return json(route, streamOpened ? [liveDelivery, baseDelivery] : [baseDelivery])
    }
    if (path === '/api/v1/inbox/stream') {
      streamOpened = true
      streamQueries.push(url.search)
      return route.fulfill({
        status: 200,
        headers: {
          'content-type': 'text/event-stream',
          'cache-control': 'no-store',
        },
        body: [
          'retry: 60000',
          'event: ready',
          'data: {"latest_delivery_id":200,"total_count":1,"unread_count":1,"acknowledged_count":0}',
          '',
          `id: ${liveDelivery.id}`,
          'event: inbox',
          `data: ${JSON.stringify(liveDelivery)}`,
          '',
          'event: state',
          'data: {"latest_delivery_id":201,"total_count":2,"unread_count":2,"acknowledged_count":0}',
          '',
          '',
        ].join('\n'),
      })
    }

    return json(route, { detail: `Unhandled multi-tab route: ${request.method()} ${path}` }, 500)
  })
}

async function mockRevokedSessionApi(page: Page) {
  const existing = delivery(300, 'Session-bound notification')
  let meCalls = 0

  await mockCommon(page)
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
        next_slice: 'Milestone 4 acceptance and stabilization',
      })
    }
    if (path === '/api/v1/me') {
      meCalls += 1
      if (meCalls > 1) return json(route, { detail: 'session revoked' }, 401)
      return json(route, {
        id: 1,
        username: 'revocation-test',
        display_name: 'Revocation Test',
        is_active: true,
        is_admin: false,
      })
    }
    if (path === '/api/v1/csrf') return json(route, { csrf_token: 'synthetic-csrf-token' })
    if (path === '/api/v1/subscriptions') return json(route, [])
    if (path === '/api/v1/inbox/state') {
      return json(route, { latest_delivery_id: 300, total_count: 1, unread_count: 1, acknowledged_count: 0 })
    }
    if (path === '/api/v1/inbox' && request.method() === 'GET') return json(route, [existing])
    if (path === '/api/v1/inbox/stream') {
      return route.fulfill({
        status: 200,
        headers: {
          'content-type': 'text/event-stream',
          'cache-control': 'no-store',
        },
        body: [
          'retry: 60000',
          'event: ready',
          'data: {"latest_delivery_id":300,"total_count":1,"unread_count":1,"acknowledged_count":0}',
          '',
          '',
        ].join('\n'),
      })
    }

    return json(route, { detail: `Unhandled revocation route: ${request.method()} ${path}` }, 500)
  })

  return () => meCalls
}

test('two tabs independently preserve the same authenticated realtime Delivery', async ({ page, context }) => {
  const streamQueries: string[] = []
  await mockMultiTabApi(page, streamQueries)
  const secondPage = await context.newPage()
  await mockMultiTabApi(secondPage, streamQueries)

  await Promise.all([page.goto('/'), secondPage.goto('/')])

  const firstList = page.locator('#notification-list')
  const secondList = secondPage.locator('#notification-list')
  await expect(firstList.getByText('Shared realtime notification', { exact: true })).toBeVisible()
  await expect(secondList.getByText('Shared realtime notification', { exact: true })).toBeVisible()
  await expect.poll(() => streamQueries.filter((query) => query.includes('after_id=200')).length).toBeGreaterThanOrEqual(2)

  await secondList.getByRole('button', { name: /Shared realtime notification/ }).click()
  await expect(secondPage.getByRole('heading', { name: 'Shared realtime notification' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Existing notification' })).toBeVisible()

  await secondPage.close()
})

test('reconnecting browser clears authenticated UI after session revocation', async ({ page }) => {
  const meCalls = await mockRevokedSessionApi(page)
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Good day, Revocation' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Session-bound notification' })).toBeVisible()
  await expect(page.getByText(/Live updates (connected|reconnecting)/)).toBeVisible()

  await expect(page.getByRole('heading', { name: 'Sign in' }), { timeout: 8_000 }).toBeVisible()
  await expect(page.locator('#notification-list')).toHaveCount(0)
  expect(meCalls()).toBeGreaterThanOrEqual(2)
})
