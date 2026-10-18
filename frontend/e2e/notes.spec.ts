import { createPatient, deletePatient, expect, test } from './helpers'

test.describe('clinical notes', () => {
  let patientId: string

  test.beforeEach(async ({ request }) => {
    patientId = (await createPatient(request, { date_of_birth: '1958-03-02' })).id
  })

  test.afterEach(async ({ request }) => {
    await deletePatient(request, patientId)
  })

  test('a note the server rejects shows why next to the field, and nothing is added', async ({
    page,
  }) => {
    await page.goto(`/patients/${patientId}`)
    const notes = page.getByRole('region', { name: /^Notes/ })
    const takenAt = page.getByLabel('Date and time of care')
    await page.getByRole('textbox', { name: 'Note' }).fill('Seen in clinic.')

    await takenAt.fill('2099-01-01T10:00')
    await page.getByRole('button', { name: 'Add note' }).click()
    await expect(takenAt).toHaveAttribute('aria-invalid', 'true')
    await expect(page.locator('#taken-at-error')).toHaveText('Cannot be in the future')

    await takenAt.fill('1950-01-01T10:00')
    await page.getByRole('button', { name: 'Add note' }).click()
    await expect(page.locator('#taken-at-error')).toHaveText(
      "Cannot be before the patient's date of birth",
    )
    await expect(notes.getByRole('heading')).toHaveText('Notes (0)')
    // What was typed is kept, so it can be corrected and saved.
    await expect(page.getByRole('textbox', { name: 'Note' })).toHaveValue('Seen in clinic.')

    await takenAt.fill('2026-01-05T10:00')
    await page.getByRole('button', { name: 'Add note' }).click()
    await expect(notes.getByRole('heading')).toHaveText('Notes (1)')
    await expect(page.locator('#taken-at-error')).toHaveCount(0)
  })

  test('deleting a note asks first, then removes it from the notes and the summary', async ({
    page,
    request,
  }) => {
    const response = await request.post(`/api/patients/${patientId}/notes`, {
      data: { taken_at: '2026-01-05T10:00:00-05:00', content: 'Entered on the wrong chart.' },
    })
    expect(response.status()).toBe(201)
    await page.goto(`/patients/${patientId}`)
    const notes = page.getByRole('region', { name: /^Notes/ })
    const summary = page.getByRole('region', { name: 'Summary' })
    await expect(notes.getByRole('heading')).toHaveText('Notes (1)')
    await expect(summary).toContainText('Entered on the wrong chart.')

    // Cancel leaves the note alone.
    await notes.getByRole('button', { name: 'Delete' }).click()
    const confirm = notes.getByRole('group', { name: 'Confirm deleting this note' })
    await confirm.getByRole('button', { name: 'Cancel' }).click()
    await expect(confirm).toHaveCount(0)
    await expect(notes.getByRole('heading')).toHaveText('Notes (1)')

    await notes.getByRole('button', { name: 'Delete' }).click()
    await confirm.getByRole('button', { name: 'Delete note' }).click()
    await expect(notes.getByRole('heading')).toHaveText('Notes (0)')
    await expect(notes).toContainText('No notes yet.')
    await expect(summary).toContainText('No clinical notes on file.')
    await expect(summary).not.toContainText('Entered on the wrong chart.')
  })

  test('a failed background refresh keeps the notes and summary on screen', async ({
    page,
    request,
  }) => {
    const response = await request.post(`/api/patients/${patientId}/notes`, {
      data: { taken_at: '2026-01-05T10:00:00-05:00', content: 'Reviewed home BP log.' },
    })
    expect(response.status()).toBe(201)
    await page.goto(`/patients/${patientId}`)
    const notes = page.getByRole('region', { name: /^Notes/ })
    const summary = page.getByRole('region', { name: 'Summary' })
    await expect(notes).toContainText('Reviewed home BP log.')
    await expect(summary).toContainText('Reviewed home BP log.')

    // From now on, reloading anything for this patient fails as if the network dropped.
    await page.route(`**/api/patients/${patientId}**`, (route) =>
      route.request().method() === 'GET' ? route.abort() : route.fallback(),
    )
    await page.evaluate(() => window.dispatchEvent(new Event('visibilitychange')))

    await expect(notes.getByRole('alert')).toContainText('Could not reach the server', {
      timeout: 10_000,
    })
    await expect(summary.getByRole('alert')).toContainText('Could not reach the server')
    await expect(notes).toContainText('Reviewed home BP log.')
    await expect(summary).toContainText('Reviewed home BP log.')
  })
})
