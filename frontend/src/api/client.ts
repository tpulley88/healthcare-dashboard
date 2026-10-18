/**
 * The one place the app talks to the API.
 *
 * Every request goes to /api on the same origin. In development Vite forwards it to FastAPI,
 * and in Docker nginx does, so the browser never needs CORS.
 */

const API_BASE = '/api'

/**
 * A failed request, with a message that is safe to show to staff.
 *
 * `fieldErrors` maps a request body field, such as "phone", to its validation message.
 * It is filled only for 422 responses that point at specific fields.
 * `status` is 0 when the server couldn't be reached at all.
 */
export class ApiError extends Error {
  readonly status: number
  readonly fieldErrors: Record<string, string>

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fieldErrors = fieldErrors
  }
}

const GENERIC_MESSAGE = 'Something went wrong. Please try again.'

/**
 * A message by status, for error responses that don't carry one from the API,
 * such as an HTML page from the proxy.
 * The API's own 4xx responses (404, 412, 422) always include a message, which is used instead.
 */
function statusMessage(status: number): string {
  if (status === 404) return 'This record could not be found. It may have been deleted.'
  // Retrying won't change a 4xx answer, so this doesn't suggest trying again.
  if (status >= 400 && status < 500) {
    return 'The request could not be completed. Reload the page and check your entries.'
  }
  // 500, 502, 503, 504: whatever the cause, staff can only wait and retry.
  if (status >= 500) return 'The server is unavailable right now. Please try again shortly.'
  return GENERIC_MESSAGE
}

interface ValidationIssue {
  loc: unknown[]
  msg: string
}

function isValidationIssue(value: unknown): value is ValidationIssue {
  if (typeof value !== 'object' || value === null) return false
  const issue = value as Record<string, unknown>
  return Array.isArray(issue.loc) && typeof issue.msg === 'string'
}

/**
 * Turn any error response into an ApiError.
 *
 * FastAPI sends `detail` as a string for most errors, and as a list of field issues for 422s.
 * Anything else, such as an HTML page from a proxy or an empty body, gets a message based
 * on the status code, so staff never see raw technical output.
 */
export async function toApiError(response: Response): Promise<ApiError> {
  let detail: unknown
  try {
    detail = ((await response.json()) as { detail?: unknown }).detail
  } catch {
    detail = undefined
  }

  if (typeof detail === 'string' && detail.trim()) {
    return new ApiError(response.status, detail)
  }

  if (Array.isArray(detail) && detail.length > 0 && detail.every(isValidationIssue)) {
    const fieldErrors: Record<string, string> = {}
    for (const issue of detail) {
      // loc looks like ["body", "phone"]. Errors about the whole body have no field name.
      const field = issue.loc[0] === 'body' ? issue.loc[1] : undefined
      if (typeof field === 'string' && !(field in fieldErrors)) {
        fieldErrors[field] = issue.msg
      }
    }
    if (Object.keys(fieldErrors).length > 0) {
      return new ApiError(response.status, 'Please correct the highlighted fields.', fieldErrors)
    }
    // A malformed id in the URL, such as a truncated link, names no record that could exist.
    if (detail.some((issue) => issue.loc[0] === 'path')) {
      return new ApiError(response.status, statusMessage(404))
    }
  }

  return new ApiError(response.status, statusMessage(response.status))
}

/**
 * Send a request and return the parsed JSON body, or throw an ApiError.
 * A 204 response returns undefined.
 */
export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { Accept: 'application/json', ...init.headers },
    })
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and try again.')
  }

  if (!response.ok) throw await toApiError(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
