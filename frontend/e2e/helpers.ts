import { test as base, expect, type APIRequestContext } from '@playwright/test'

import type { Patient, PatientInput } from '../src/api/types'

/** A name no seeded patient has, so tests never touch each other's records or the seed. */
export function uniqueLastName(): string {
  return `Playwright${Math.random().toString(36).slice(2, 8)}`
}

export async function createPatient(
  request: APIRequestContext,
  fields: Partial<PatientInput> = {},
): Promise<Patient> {
  const response = await request.post('/api/patients', {
    data: {
      first_name: 'Ana',
      last_name: uniqueLastName(),
      date_of_birth: '1958-03-02',
      ...fields,
    },
  })
  expect(response.status()).toBe(201)
  return response.json()
}

/** Remove a test patient. A patient the test already deleted returns 404, which is fine. */
export async function deletePatient(request: APIRequestContext, id: string): Promise<void> {
  const response = await request.delete(`/api/patients/${id}`)
  expect([204, 404]).toContain(response.status())
}

/**
 * Playwright's `test`, except every summary request asks for the built-in summary,
 * so the suite never calls the language model, even when the server has a key.
 * A test can still answer the summary request itself with its own `page.route`,
 * which takes precedence.
 */
export const test = base.extend({
  // The second argument is usually called `use`; renamed so the React hooks lint rule ignores it.
  context: async ({ context }, provide) => {
    await context.route('**/api/patients/*/summary', (route) => {
      const url = new URL(route.request().url())
      url.searchParams.set('source', 'template')
      return route.fallback({ url: url.toString() })
    })
    await provide(context)
  },
})

export { expect }
