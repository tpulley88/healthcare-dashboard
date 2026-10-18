import { expect, test } from './helpers'
test('the dashboard is home, and the sidebar moves between sections', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Dashboard', level: 1 })).toBeVisible()

  const sidebar = page.getByRole('navigation', { name: 'Main' })
  await expect(sidebar.getByRole('link', { name: 'Dashboard' })).toHaveAttribute(
    'aria-current',
    'page',
  )

  // Counts load from the API; seeded data always has active patients.
  const active = page.getByRole('link', { name: /Active/ })
  await expect(active).toContainText(/\d+/)
  await active.click()
  await expect(page).toHaveURL('/patients?status=active')
  await expect(page.getByLabel('Status')).toHaveValue('active')
  await expect(sidebar.getByRole('link', { name: 'Patients' })).toHaveAttribute(
    'aria-current',
    'page',
  )

  await sidebar.getByRole('link', { name: 'Dashboard' }).click()
  await expect(page).toHaveURL('/')
})

test('the header offers a new patient from any page', async ({ page }) => {
  await page.goto('/patients')
  await page.getByRole('link', { name: 'New patient' }).click()
  await expect(page.getByRole('heading', { name: 'New patient' })).toBeVisible()
})

test('unknown addresses show the not-found page', async ({ page }) => {
  await page.goto('/no-such-page')
  await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible()
})

test('on a phone-sized screen the layout fits without sideways scrolling', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 740 })
  for (const path of ['/', '/patients/new']) {
    await page.goto(path)
    await expect(page.getByRole('navigation', { name: 'Main' })).toBeVisible()
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    )
    expect(overflow, `horizontal overflow on ${path}`).toBeLessThanOrEqual(0)
  }
})

test('finding a patient from the dashboard opens the searched list', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('searchbox', { name: 'Find a patient' }).fill('  Ana ')
  await page.getByRole('button', { name: 'Search' }).click()
  await expect(page).toHaveURL('/patients?search=Ana')
  await expect(page.getByRole('searchbox', { name: 'Search' })).toHaveValue('Ana')
})
