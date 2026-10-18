import { deletePatient, expect, test, uniqueLastName } from './helpers'

test('create a patient, chart a note, edit, and delete', async ({ page, request }) => {
  const lastName = uniqueLastName()
  let patientId: string | undefined

  try {
    await page.goto('/patients/new')
    await page.getByLabel('First name').fill('Maya')
    await page.getByLabel('Last name').fill(lastName)
    await page.getByLabel('Date of birth').fill('1980-05-14')

    // "Has allergies" with nothing entered is caught before anything is sent.
    const allergies = page.getByRole('group', { name: 'Allergies' })
    await allergies.getByRole('radio', { name: 'Has allergies' }).check()
    await page.getByRole('button', { name: 'Create patient' }).click()
    await expect(allergies).toContainText('Enter at least one')
    await allergies.getByLabel('One per line').fill('Sulfa drugs')

    // The API's own validation messages appear next to the field.
    await page.getByLabel('Phone').fill('555-0142')
    await page.getByRole('button', { name: 'Create patient' }).click()
    await expect(page.locator('#patient-phone-error')).toBeVisible()
    await page.getByLabel('Phone').fill('617-555-0142')
    await page.getByRole('button', { name: 'Create patient' }).click()

    await expect(page).toHaveURL(/\/patients\/[0-9a-f-]{36}$/)
    patientId = page.url().split('/').pop()
    await expect(page.getByRole('heading', { name: `Maya ${lastName}` })).toBeVisible()
    await expect(page.locator('.allergy-banner')).toContainText('Sulfa drugs')
    await expect(page.locator('.details')).toContainText('(617) 555-0142')

    // A new note appears in the notes list and the summary.
    await page
      .getByRole('textbox', { name: 'Note' })
      .fill('Seen for a routine check. Feeling well.')
    await page.getByRole('button', { name: 'Add note' }).click()
    await expect(page.getByRole('heading', { name: 'Notes (1)' })).toBeVisible()
    await expect(page.locator('.timeline')).toContainText('Seen for a routine check.')

    await page.getByRole('link', { name: 'Edit patient' }).click()
    await page.getByLabel('Status').selectOption('inactive')
    await page.getByRole('button', { name: 'Save changes' }).click()
    await expect(page).toHaveURL(`/patients/${patientId}`)
    await expect(page.locator('.chart-title')).toContainText('Inactive')

    await page.getByRole('button', { name: 'Delete patient' }).click()
    await page
      .getByRole('group', { name: 'Confirm deleting this patient' })
      .getByRole('button', { name: 'Delete patient' })
      .click()
    await expect(page).toHaveURL('/patients')
    await page.getByLabel('Search').fill(lastName)
    await expect(page.getByText('No patients match')).toBeVisible()
  } finally {
    if (patientId) await deletePatient(request, patientId)
  }
})
