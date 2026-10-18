import type { Page } from '@playwright/test'

import { createPatient, deletePatient, expect, test } from './helpers'

async function openEdit(page: Page, id: string) {
  await page.goto(`/patients/${id}/edit`)
  await expect(page.getByRole('heading', { name: /^Edit / })).toBeVisible()
}

async function setAllergies(page: Page, entries: string[]) {
  const allergies = page.getByRole('group', { name: 'Allergies' })
  await allergies.getByRole('radio', { name: 'Has allergies' }).check()
  await allergies.getByLabel('One per line').fill(entries.join('\n'))
}

test.describe('two people editing the same patient', () => {
  let patientId: string

  test.beforeEach(async ({ request }) => {
    const patient = await createPatient(request, {
      allergies: ['Penicillin'],
      phone: '(617) 555-0100',
      city: 'Boston',
    })
    patientId = patient.id
  })

  test.afterEach(async ({ request }) => {
    await deletePatient(request, patientId)
  })

  test('different fields: the second save keeps both changes after review', async ({ context }) => {
    // Both tabs open the edit page before either saves.
    const colleague = await context.newPage()
    const me = await context.newPage()
    await openEdit(colleague, patientId)
    await openEdit(me, patientId)

    await setAllergies(colleague, ['Penicillin', 'Latex'])
    await colleague.getByRole('button', { name: 'Save changes' }).click()
    await expect(colleague).toHaveURL(`/patients/${patientId}`)

    await me.getByLabel('Phone').fill('617-555-0199')
    await me.getByRole('button', { name: 'Save changes' }).click()

    const panel = me.getByRole('alert').filter({ hasText: 'Someone else changed this patient' })
    await expect(panel).toBeVisible()
    const row = panel.getByRole('row', { name: /Allergies/ })
    await expect(row).toContainText('Penicillin, Latex')
    await expect(panel.getByText('You both changed this')).toHaveCount(0)
    // Saving is blocked until a choice is made.
    await expect(me.getByRole('button', { name: 'Save changes' })).toBeDisabled()

    await panel.getByRole('button', { name: 'Keep my changes and review' }).click()
    await expect(panel).toBeHidden()
    // Their allergy change is now in my form, with my phone edit on top.
    await expect(
      me.getByRole('group', { name: 'Allergies' }).getByLabel('One per line'),
    ).toHaveValue('Penicillin\nLatex')
    await expect(me.getByLabel('Phone')).toHaveValue('617-555-0199')

    await me.getByRole('button', { name: 'Save changes' }).click()
    await expect(me).toHaveURL(`/patients/${patientId}`)
    await expect(me.locator('.allergy-banner')).toContainText('Penicillin, Latex')
    await expect(me.locator('.details')).toContainText('(617) 555-0199')
  })

  test('same field: the overlap is flagged, and discarding keeps their value', async ({
    context,
  }) => {
    const colleague = await context.newPage()
    const me = await context.newPage()
    await openEdit(colleague, patientId)
    await openEdit(me, patientId)

    await colleague.getByLabel('City').fill('Cambridge')
    await colleague.getByRole('button', { name: 'Save changes' }).click()
    await expect(colleague).toHaveURL(`/patients/${patientId}`)

    await me.getByLabel('City').fill('Somerville')
    await me.getByRole('button', { name: 'Save changes' }).click()

    const panel = me.getByRole('alert').filter({ hasText: 'Someone else changed this patient' })
    const row = panel.getByRole('row', { name: /City/ })
    await expect(row).toContainText('You both changed this')
    await expect(row).toContainText('Boston')
    await expect(row).toContainText('Cambridge')
    await expect(row).toContainText('Somerville')

    await panel.getByRole('button', { name: 'Discard my changes' }).click()
    await expect(me.getByLabel('City')).toHaveValue('Cambridge')
    // Nothing left to save until I change something.
    await expect(me.getByRole('button', { name: 'Save changes' })).toBeDisabled()
  })
})

test('a failed background refresh keeps unsaved edits on screen', async ({ page, request }) => {
  const patient = await createPatient(request, { city: 'Boston' })
  try {
    await openEdit(page, patient.id)
    await page.getByLabel('City').fill('Edited but not saved')

    // From now on, reloading this patient fails as if the network dropped.
    await page.route(`**/api/patients/${patient.id}`, (route) =>
      route.request().method() === 'GET' ? route.abort() : route.fallback(),
    )
    // Returning to the tab makes the app refresh the patient in the background.
    await page.evaluate(() => window.dispatchEvent(new Event('visibilitychange')))

    await expect(page.getByRole('alert')).toContainText('Could not reach the server', {
      timeout: 10_000,
    })
    await expect(page.getByLabel('City')).toHaveValue('Edited but not saved')
  } finally {
    await deletePatient(request, patient.id)
  }
})
