import type { Page } from '@playwright/test'

import { createPatient, deletePatient, expect, test, uniqueLastName } from './helpers'

function rowNames(page: Page) {
  return page.locator('tbody tr td:first-child')
}

test.describe('patient list', () => {
  const lastName = uniqueLastName()
  const ids: string[] = []

  // Three patients who share a last name, so a search for it finds only them.
  test.beforeAll(async ({ request }) => {
    for (const [first_name, date_of_birth, status] of [
      ['Ava', '1990-04-10', 'active'],
      ['Ben', '1950-04-10', 'inactive'],
      ['Cy', '2010-04-10', 'active'],
    ] as const) {
      ids.push(
        (await createPatient(request, { first_name, last_name: lastName, date_of_birth, status }))
          .id,
      )
    }
  })

  test.afterAll(async ({ request }) => {
    for (const id of ids) await deletePatient(request, id)
  })

  test('search, filter, and sort live in the URL, so Back and reload keep the view', async ({
    page,
  }) => {
    await page.goto('/patients')
    await page.getByRole('searchbox', { name: 'Search' }).fill(lastName)
    await expect(page).toHaveURL(`/patients?search=${lastName}`)
    await expect(page.getByText('Showing 1–3 of 3 patients')).toBeVisible()
    await expect(rowNames(page)).toHaveText([
      `${lastName}, Ava`,
      `${lastName}, Ben`,
      `${lastName}, Cy`,
    ])

    // Age: youngest first, then oldest first on a second click.
    const age = page.getByRole('columnheader', { name: 'Age' })
    await age.getByRole('button').click()
    await expect(age).toHaveAttribute('aria-sort', 'ascending')
    await expect(rowNames(page)).toHaveText([
      `${lastName}, Cy`,
      `${lastName}, Ava`,
      `${lastName}, Ben`,
    ])
    await age.getByRole('button').click()
    await expect(age).toHaveAttribute('aria-sort', 'descending')
    await expect(rowNames(page)).toHaveText([
      `${lastName}, Ben`,
      `${lastName}, Ava`,
      `${lastName}, Cy`,
    ])

    await page.getByLabel('Status').selectOption('inactive')
    await expect(page).toHaveURL(/status=inactive/)
    await expect(rowNames(page)).toHaveText([`${lastName}, Ben`])

    // Back undoes the filter but keeps the search and sort.
    await page.goBack()
    await expect(page.getByLabel('Status')).toHaveValue('')
    await expect(rowNames(page)).toHaveText([
      `${lastName}, Ben`,
      `${lastName}, Ava`,
      `${lastName}, Cy`,
    ])

    await page.reload()
    await expect(page.getByRole('searchbox', { name: 'Search' })).toHaveValue(lastName)
    await expect(age).toHaveAttribute('aria-sort', 'descending')
    await expect(rowNames(page)).toHaveCount(3)
  })

  test('a search with no matches says so', async ({ page }) => {
    await page.goto(`/patients?search=${lastName}&status=deceased`)
    await expect(page.getByText('No patients match this search.')).toBeVisible()
  })
})

test('paging moves through the list, and Back returns to the previous page', async ({ page }) => {
  // The seeded practice has well over one page of patients.
  await page.goto('/patients')
  const pages = page.getByRole('navigation', { name: 'Pages' })
  await expect(pages).toContainText(/Showing 1–20 of \d+ patients/)
  await expect(pages.getByRole('button', { name: 'Previous' })).toBeDisabled()
  const firstOnPageOne = await rowNames(page).first().textContent()

  await pages.getByRole('button', { name: 'Next' }).click()
  await expect(page).toHaveURL('/patients?page=2')
  await expect(pages).toContainText(/Showing 21–40 of \d+ patients/)
  await expect(rowNames(page).first()).not.toHaveText(firstOnPageOne ?? '')
  await expect(rowNames(page)).toHaveCount(20)

  await page.goBack()
  await expect(pages).toContainText(/Showing 1–20 of/)
  await expect(rowNames(page).first()).toHaveText(firstOnPageOne ?? '')
})

test('a deceased patient shows no age, because no date of death is recorded', async ({
  page,
  request,
}) => {
  const lastName = uniqueLastName()
  const patient = await createPatient(request, { last_name: lastName, status: 'deceased' })
  try {
    await page.goto(`/patients?search=${lastName}`)
    const row = page.locator('tbody tr')
    await expect(row).toHaveCount(1)
    await expect(row.locator('td').nth(1)).toHaveText('—')
  } finally {
    await deletePatient(request, patient.id)
  }
})
