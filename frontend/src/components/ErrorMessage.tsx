import { ApiError } from '../api/client'

const FALLBACK = 'Something went wrong. Please try again.'

/** Shows a failed request in plain language, with a retry button when one is given. */
export function ErrorMessage({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  // Only ApiError messages are written for staff. Anything else may be a raw technical error.
  const message = error instanceof ApiError ? error.message : FALLBACK
  return (
    <div className="notice notice-error" role="alert">
      <p>{message}</p>
      {onRetry && (
        <button type="button" className="button" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}
