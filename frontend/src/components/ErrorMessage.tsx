import { ApiError } from '../api/client'

const FALLBACK = 'Something went wrong. Please try again.'

/** Shows a failed request in plain language, with a retry button when retrying could help. */
export function ErrorMessage({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  // Only ApiError messages are written for staff. Anything else may be a raw technical error.
  const message = error instanceof ApiError ? error.message : FALLBACK
  // Retrying a 4xx, such as a deleted patient, would only get the same answer.
  const retryable = !(error instanceof ApiError && error.status >= 400 && error.status < 500)
  return (
    <div className="notice notice-error" role="alert">
      <p>{message}</p>
      {onRetry && retryable && (
        <button type="button" className="button" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}
