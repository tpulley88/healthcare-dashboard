import { createPatient, deletePatient, expect, test } from './helpers'
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

test('a failed background refresh keeps the dashboard on screen', async ({ page }) => {
  await page.goto('/')
  const counts = page.getByRole('list', { name: 'Patients by status' })
  const recent = page.getByRole('region', { name: 'Patients with recent visits' })
  await expect(counts.getByRole('link', { name: /All patients/ })).toContainText(/\d+/)
  await expect(recent.getByRole('listitem').first()).toBeVisible()

  await page.route('**/api/patients?**', (route) => route.abort())
  await page.evaluate(() => window.dispatchEvent(new Event('visibilitychange')))

  await expect(page.getByRole('alert').first()).toContainText('Could not reach the server', {
    timeout: 10_000,
  })
  await expect(counts.getByRole('link', { name: /All patients/ })).toContainText(/\d+/)
  await expect(recent.getByRole('listitem').first()).toBeVisible()
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

test("a deleted patient's chart says it can't be found, without offering a retry", async ({
  page,
  request,
}) => {
  const { id } = await createPatient(request)
  await deletePatient(request, id)
  await page.goto(`/patients/${id}`)
  await expect(page.getByRole('alert')).toHaveText('Patient not found')
  await expect(page.getByRole('button', { name: 'Try again' })).toHaveCount(0)
  await page.getByRole('link', { name: '← All patients' }).click()
  await expect(page).toHaveURL('/patients')
})

test('on a phone-sized screen the layout fits without sideways scrolling', async ({
  page,
  request,
}) => {
  // Long values are the usual cause of sideways scrolling.
  const patient = await createPatient(request, {
    email: 'firstname.middlename.lastname@example-family-practice.com',
  })
  const loaded = {
    '/': page.getByRole('heading', { name: 'Dashboard', level: 1 }),
    '/patients': page.getByRole('row').nth(1),
    [`/patients/${patient.id}`]: page.getByRole('region', { name: 'Summary' }),
    [`/patients/${patient.id}/edit`]: page.getByLabel('First name'),
    '/patients/new': page.getByLabel('First name'),
  }
  try {
    await page.setViewportSize({ width: 320, height: 740 })
    for (const [path, content] of Object.entries(loaded)) {
      await page.goto(path)
      await expect(content).toBeVisible()
      await expect(page.locator('[aria-busy="true"]')).toHaveCount(0)
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      )
      expect(overflow, `horizontal overflow on ${path}`).toBeLessThanOrEqual(0)
    }

    // The list keeps the columns a clinician scans for; the rest are in the chart.
    await page.goto('/patients')
    for (const name of ['Name', 'Age', 'Status', 'Allergies', 'Last visit']) {
      await expect(page.getByRole('columnheader', { name })).toBeVisible()
    }
    for (const name of ['Date of birth', 'Conditions', 'Phone']) {
      await expect(page.getByRole('columnheader', { name })).toBeHidden()
    }
  } finally {
    await deletePatient(request, patient.id)
  }
})

test('finding a patient from the dashboard opens the searched list', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('searchbox', { name: 'Find a patient' }).fill('  Ana ')
  await page.getByRole('button', { name: 'Search' }).click()
  await expect(page).toHaveURL('/patients?search=Ana')
  await expect(page.getByRole('searchbox', { name: 'Search' })).toHaveValue('Ana')
})
