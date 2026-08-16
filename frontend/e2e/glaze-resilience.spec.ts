import { expect, test, type Page, type Route } from '@playwright/test'

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

async function mockSignedOut(page: Page) {
  await page.route('**/healthz', (route) => json(route, {
    status: 'ok',
    service: 'GoreeCloud Notify',
    version: '0.1.0-dev',
  }))

  await page.route('**/api/v1/**', (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/meta') {
      return json(route, {
        service: 'GoreeCloud Notify',
        version: '0.1.0-dev',
        milestone: 1,
        development_milestone: 4,
        production: false,
        implemented_engine: ['Glaze UI appearance resilience'],
        next_milestone: 'Real-Time Delivery',
        next_slice: 'Acceptance and stabilization',
      })
    }
    if (path === '/api/v1/me') return json(route, { detail: 'not authenticated' }, 401)
    return json(route, { detail: `Unhandled Glaze resilience route: ${path}` }, 500)
  })
}

test('Auto appearance uses the light Glaze background on a light operating-system theme', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' })
  await mockSignedOut(page)
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'system')

  const appearance = await page.evaluate(() => ({
    background: getComputedStyle(document.body).backgroundImage,
    backgroundToken: getComputedStyle(document.documentElement).getPropertyValue('--bg').trim(),
  }))

  expect(appearance.backgroundToken).toBe('#edf3fa')
  expect(appearance.background).toContain('rgba(255, 255, 255, 0.9)')
  expect(appearance.background).not.toContain('rgba(67, 90, 123, 0.42)')
})

test('Auto appearance follows a dark operating-system theme', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' })
  await mockSignedOut(page)
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'system')

  const appearance = await page.evaluate(() => ({
    background: getComputedStyle(document.body).backgroundImage,
    backgroundToken: getComputedStyle(document.documentElement).getPropertyValue('--bg').trim(),
  }))

  expect(appearance.backgroundToken).toBe('#0e151f')
  expect(appearance.background).toContain('rgba(67, 90, 123, 0.42)')
})

test('blocked browser preference storage does not prevent Notify from opening', async ({ page }) => {
  await page.addInitScript(() => {
    const blocked = () => {
      throw new DOMException('Browser storage blocked for resilience validation', 'SecurityError')
    }
    Storage.prototype.getItem = blocked
    Storage.prototype.setItem = blocked
    Storage.prototype.removeItem = blocked
  })

  await mockSignedOut(page)
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'system')
  await expect(page.getByText('One calm place for operational and GoreeCloud application notifications')).toBeVisible()
})
