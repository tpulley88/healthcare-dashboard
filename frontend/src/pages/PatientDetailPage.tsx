import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'

import { getPatient } from '../api/patients'
import { ErrorMessage } from '../components/ErrorMessage'
import { fullName } from '../format'

// Placeholder for M6, which adds the profile, summary, and notes.
export function PatientDetailPage() {
  const { patientId = '' } = useParams()
  const { data, error, isPending, refetch } = useQuery({
    queryKey: ['patient', patientId],
    queryFn: () => getPatient(patientId),
  })

  return (
    <section>
      <p>
        <Link to="/patients">← All patients</Link>
      </p>
      {isPending ? (
        <p className="muted">Loading patient…</p>
      ) : error ? (
        <ErrorMessage error={error} onRetry={() => refetch()} />
      ) : (
        <h1>{fullName(data)}</h1>
      )}
    </section>
  )
}
