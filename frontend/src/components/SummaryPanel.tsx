import { useQuery } from '@tanstack/react-query'

import { getSummary } from '../api/notes'
import { coverageLabel } from '../format'
import { ErrorMessage } from './ErrorMessage'

/**
 * The generated summary, labeled so nobody mistakes it for a full chart review.
 * Each note contributes only its opening sentence or two, so the full notes stay on the
 * same page, one link away.
 */
export function SummaryPanel({ patientId }: { patientId: string }) {
  const { data, error, isPending, refetch } = useQuery({
    queryKey: ['patient', patientId, 'summary'],
    queryFn: () => getSummary(patientId),
  })

  return (
    <section className="card" aria-labelledby="summary-heading">
      <h2 id="summary-heading">Summary</h2>
      {isPending ? (
        <p className="muted">Loading summary…</p>
      ) : error ? (
        <ErrorMessage error={error} onRetry={() => refetch()} />
      ) : (
        <>
          <p className="coverage">{coverageLabel(data)}</p>
          <p className="summary-headline">{data.headline}</p>
          {/* The API puts each note on its own line. */}
          <ul className="timeline">
            {data.narrative.split('\n').map((line, index) => (
              <li key={index}>{line}</li>
            ))}
          </ul>
          {data.notes_total > 0 && (
            <p className="muted small">
              Each note contributes only its first sentence or two, so details later in a note may
              be missing. <a href="#notes-heading">Read the full notes</a>.
            </p>
          )}
        </>
      )}
    </section>
  )
}
