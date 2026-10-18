import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, request } from './client'

function respondWith(status: number, body: string, contentType = 'application/json') {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(body, { status, headers: { 'Content-Type': contentType } })),
  )
}

async function errorFrom(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise
  } catch (error) {
    expect(error).toBeInstanceOf(ApiError)
    return error as ApiError
  }
  throw new Error('Expected the request to fail')
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('request', () => {
  it('returns the parsed body on success', async () => {
    respondWith(200, '{"status":"ok"}')
    await expect(request('/health')).resolves.toEqual({ status: 'ok' })
  })

  it('returns undefined for 204 No Content', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(null, { status: 204 })),
    )
    await expect(request('/patients/1', { method: 'DELETE' })).resolves.toBeUndefined()
  })

  it('uses a string detail as the message', async () => {
    respondWith(404, '{"detail":"Patient not found"}')
    const error = await errorFrom(request('/patients/1'))
    expect(error.status).toBe(404)
    expect(error.message).toBe('Patient not found')
  })

  it('maps 422 field issues to their fields, keeping the first message per field', async () => {
    const detail = [
      { loc: ['body', 'phone'], msg: 'Must be a 10-digit US phone number', type: 'value_error' },
      { loc: ['body', 'phone'], msg: 'A second message', type: 'value_error' },
      { loc: ['body', 'first_name'], msg: 'Field required', type: 'missing' },
      { loc: ['body'], msg: 'Invalid JSON', type: 'json_invalid' },
    ]
    respondWith(422, JSON.stringify({ detail }))
    const error = await errorFrom(request('/patients', { method: 'POST' }))
    expect(error.fieldErrors).toEqual({
      phone: 'Must be a 10-digit US phone number',
      first_name: 'Field required',
    })
    expect(error.message).toBe('Please correct the highlighted fields.')
  })

  it.each([
    ['an HTML error page', 502, '<html>Bad Gateway</html>', 'text/html'],
    ['an empty body', 500, '', 'application/json'],
    ['an unexpected JSON shape', 400, '{"error":{"code":7}}', 'application/json'],
    ['a detail list in an unexpected shape', 422, '{"detail":[{"oops":true}]}', 'application/json'],
  ])('falls back to a readable message for %s', async (_case, status, body, contentType) => {
    respondWith(status, body, contentType)
    const error = await errorFrom(request('/patients'))
    expect(error.status).toBe(status)
    expect(error.message).not.toMatch(/<html|oops|code/)
    expect(error.message).toMatch(/^[A-Z]/)
    expect(error.fieldErrors).toEqual({})
  })

  it.each([500, 502, 503, 504])(
    'gives every %i without a message the same server message',
    async (status) => {
      respondWith(status, '<html>Error</html>', 'text/html')
      const error = await errorFrom(request('/patients'))
      expect(error.message).toBe('The server is unavailable right now. Please try again shortly.')
    },
  )

  it.each([400, 409, 413])('does not suggest retrying a %i without a message', async (status) => {
    respondWith(status, '', 'text/html')
    const error = await errorFrom(request('/patients'))
    expect(error.message).toBe(
      'The request could not be completed. Reload the page and check your entries.',
    )
  })

  it('reports a network failure as status 0', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))),
    )
    const error = await errorFrom(request('/patients'))
    expect(error.status).toBe(0)
    expect(error.message).toMatch(/Could not reach the server/)
  })
})
