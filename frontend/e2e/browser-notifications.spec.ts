import { expect, test, type Page, type Route } from '@playwright/test'

type Delivery = {
  id: number
  notification_id: number
  source: string
  channel: string
  title: string
  body: string
  severity: 'warning'
  notification_created_at: string
  delivered_at: string
  expires_at: null
  read_at: null
  acknowledged_at: null
}

const timestamp = '2026-08-14T16:00:00Z'

function delivery(id: number, title: string): Delivery {
  return {
    id,
    notification_id: id + 1_000,
    source: 'private-sensitive-source',
    channel: 'private-sensitive-channel',
    title,
    body: `Private body for ${title}`,
    severity: 'warning',
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

async function installFakeNotificationApi(
  page: Page,
  initialPermission: NotificationPermission = 'default',
  requestPermissionResult: NotificationPermission = 'granted',
) {
  await page.addInitScript({
    content: `
      window.__notifyPermissionRequests = 0;
      window.__notifySystemAlerts = [];
      window.__notifyVisibilityState = 'visible';
      Object.defineProperty(document, 'visibilityState', {
        configurable: true,
        get() { return window.__notifyVisibilityState; }
      });
      class FakePermissionStatus extends EventTarget {
        get state() {
          return FakeNotification.permission === 'granted'
            ? 'granted'
            : FakeNotification.permission === 'denied' ? 'denied' : 'prompt';
        }
      }
      class FakeNotification {
        static permission = ${JSON.stringify(initialPermission)};
        static async requestPermission() {
          window.__notifyPermissionRequests += 1;
          FakeNotification.permission = ${JSON.stringify(requestPermissionResult)};
          return FakeNotification.permission;
        }
        constructor(title, options = {}) {
          this.title = title;
          this.body = options.body || '';
          this.onclick = null;
          window.__notifySystemAlerts.push({ title, body: this.body });
        }
        close() {}
      }
      const permissionStatus = new FakePermissionStatus();
      window.__notifyPermissionStatus = permissionStatus;
      Object.defineProperty(window, 'Notification', {
        configurable: true,
        value: FakeNotification
      });
      Object.defineProperty(navigator, 'permissions', {
        configurable: true,
        value: {
          async query(descriptor) {
            if (descriptor && descriptor.name === 'notifications') return permissionStatus;
            throw new TypeError('Unsupported permission descriptor');
          }
        }
      });
    `,
  })
}

async function mockPrivacyScenario(page: Page) {
  const replay = delivery(151, 'Sensitive replay title')
  const hiddenNew = delivery(152, 'Sensitive hidden new title')
  const visibleNew = delivery(153, 'Sensitive visible new title')
  let streamNumber = 0
  const streamQueries: string[] = []

  await page.route('**/healthz', (route) => json(route, {
    status: 'ok', service: 'GoreeCloud Notify', version: '0.2.0',
  }))
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname

    if (path === '/api/v1/meta') {
      return json(route, {
        service: 'GoreeCloud Notify',
        version: '0.2.0',
        build_revision: 'dd22a7ad0765c8ca62b401749265594bb0a06e23',
        milestone: 1,
        development_milestone: 4,
        production: false,
        release_stage: 'release_candidate',
        implemented_engine: ['authenticated SSE inbox stream'],
        next_milestone: 'Production Acceptance',
        next_slice: 'Target deployment and controlled acceptance',
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
    if (path === '/api/v1/csrf') return json(route, { csrf_token: 'synthetic-csrf-token' })
    if (path === '/api/v1/subscriptions') return json(route, [])
    if (path === '/api/v1/inbox/state') {
      return json(route, {
        latest_delivery_id: 150,
        total_count: 120,
        unread_count: 37,
        acknowledged_count: 22,
      })
    }
    if (path === '/api/v1/inbox' && request.method() === 'GET') return json(route, [])

    if (path === '/api/v1/inbox/stream') {
      streamNumber += 1
      streamQueries.push(url.search)
      const events = streamNumber === 1
        ? [
            'retry: 60000',
            'event: ready',
            'data: {"cursor":150,"latest_delivery_id":150,"total_count":120,"unread_count":37,"acknowledged_count":22}',
            '',
            '',
          ]
        : streamNumber === 2
          ? [
              'retry: 60000',
              'event: ready',
              'data: {"cursor":150,"latest_delivery_id":151,"total_count":121,"unread_count":38,"acknowledged_count":22}',
              '',
              `id: ${replay.id}`,
              'event: inbox',
              `data: ${JSON.stringify(replay)}`,
              '',
              `id: ${hiddenNew.id}`,
              'event: inbox',
              `data: ${JSON.stringify(hiddenNew)}`,
              '',
              '',
            ]
          : [
              'retry: 60000',
              'event: ready',
              `data: {"cursor":${hiddenNew.id},"latest_delivery_id":${hiddenNew.id},"total_count":122,"unread_count":39,"acknowledged_count":22}`,
              '',
              `id: ${visibleNew.id}`,
              'event: inbox',
              `data: ${JSON.stringify(visibleNew)}`,
              '',
              '',
            ]

      return route.fulfill({
        status: 200,
        headers: { 'content-type': 'text/event-stream', 'cache-control': 'no-store' },
        body: events.join('\n'),
      })
    }

    return json(route, { detail: `Unhandled privacy test route: ${request.method()} ${path}` }, 500)
  })

  return { replay, hiddenNew, visibleNew, streamQueries }
}

test('system alerts require explicit opt-in and redact Delivery details', async ({ page, context }) => {
  await installFakeNotificationApi(page)
  const evidence = await mockPrivacyScenario(page)
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Good day, Browser' })).toBeVisible()
  await expect.poll(() => page.evaluate(() => (window as typeof window & { __notifyPermissionRequests: number }).__notifyPermissionRequests)).toBe(0)

  await page.getByText('System alerts', { exact: true }).click()
  await expect(page.getByText(/Off by default\. Notify will ask for browser permission only after you choose/)).toBeVisible()
  await expect(page.getByText(/Operating-system alerts do not include the notification title, body, source, channel/)).toBeVisible()

  await page.getByRole('button', { name: 'Enable system alerts' }).click()
  await expect.poll(() => page.evaluate(() => (window as typeof window & { __notifyPermissionRequests: number }).__notifyPermissionRequests)).toBe(1)
  await expect(page.getByText('Enabled locally')).toBeVisible()

  await page.evaluate(() => {
    ;(window as typeof window & { __notifyVisibilityState: string }).__notifyVisibilityState = 'hidden'
    document.dispatchEvent(new Event('visibilitychange'))
  })
  await context.setOffline(true)
  await expect(page.getByText(/Live updates offline/)).toBeVisible()
  await context.setOffline(false)

  await expect.poll(() => evidence.streamQueries.some((query) => query.includes('after_id=150'))).toBe(true)
  await expect.poll(() => page.evaluate(() => (window as typeof window & { __notifySystemAlerts: Array<{ title: string; body: string }> }).__notifySystemAlerts.length)).toBe(1)

  const alerts = await page.evaluate(() => (window as typeof window & { __notifySystemAlerts: Array<{ title: string; body: string }> }).__notifySystemAlerts)
  expect(alerts).toEqual([{
    title: 'GoreeCloud Notify',
    body: 'A new notification is available. Open Notify to view details.',
  }])
  const leakedValues = [
    evidence.replay.title,
    evidence.replay.body,
    evidence.hiddenNew.title,
    evidence.hiddenNew.body,
    evidence.hiddenNew.source,
    evidence.hiddenNew.channel,
  ]
  for (const privateValue of leakedValues) {
    expect(JSON.stringify(alerts)).not.toContain(privateValue)
  }

  await page.evaluate(() => {
    ;(window as typeof window & { __notifyVisibilityState: string }).__notifyVisibilityState = 'visible'
    document.dispatchEvent(new Event('visibilitychange'))
  })
  await context.setOffline(true)
  await expect(page.getByText(/Live updates offline/)).toBeVisible()
  await context.setOffline(false)
  await page.evaluate(() => window.dispatchEvent(new Event('online')))
  await expect.poll(
    () => evidence.streamQueries.some((query) => query.includes('after_id=152')),
    { timeout: 8_000 },
  ).toBe(true)
  await expect.poll(() => page.evaluate(() => (window as typeof window & { __notifySystemAlerts: unknown[] }).__notifySystemAlerts.length)).toBe(1)
  await expect(page.locator('#notification-list').getByText(evidence.visibleNew.title, { exact: true })).toBeVisible()
})

test('browser denial remains fail-closed and does not persist local opt-in', async ({ page }) => {
  await installFakeNotificationApi(page, 'default', 'denied')
  await mockPrivacyScenario(page)
  await page.goto('/')

  await page.getByText('System alerts', { exact: true }).click()
  await expect(page.getByText('Permission not requested')).toBeVisible()
  await page.getByRole('button', { name: 'Enable system alerts' }).click()

  await expect.poll(() => page.evaluate(() => (window as typeof window & { __notifyPermissionRequests: number }).__notifyPermissionRequests)).toBe(1)
  await expect(page.getByText('Blocked by browser', { exact: true })).toBeVisible()
  await expect(page.getByText('Permission blocked', { exact: true })).toBeVisible()
  await expect(page.getByText(/This browser has blocked system alerts/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Enable system alerts' })).toBeDisabled()
  await expect.poll(() => page.evaluate(() => window.localStorage.getItem('goreecloud-notify-system-alerts'))).toBeNull()
  await expect.poll(() => page.evaluate(() => (window as typeof window & { __notifySystemAlerts: unknown[] }).__notifySystemAlerts.length)).toBe(0)
})

test('external permission revocation is reconciled from the Permissions API change signal', async ({ page }) => {
  await installFakeNotificationApi(page)
  await mockPrivacyScenario(page)
  await page.goto('/')

  await page.getByText('System alerts', { exact: true }).click()
  await page.getByRole('button', { name: 'Enable system alerts' }).click()
  await expect(page.getByText('Enabled locally')).toBeVisible()
  await expect.poll(() => page.evaluate(() => window.localStorage.getItem('goreecloud-notify-system-alerts'))).toBe('enabled')

  await page.evaluate(() => {
    Object.defineProperty(window.Notification, 'permission', {
      configurable: true,
      writable: true,
      value: 'denied',
    })
    ;(window as typeof window & { __notifyPermissionStatus: EventTarget }).__notifyPermissionStatus.dispatchEvent(new Event('change'))
  })

  await expect(page.getByText('Blocked by browser', { exact: true })).toBeVisible()
  await expect(page.getByText('Permission blocked', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Enable system alerts' })).toBeDisabled()
  await expect.poll(() => page.evaluate(() => window.localStorage.getItem('goreecloud-notify-system-alerts'))).toBeNull()
})
