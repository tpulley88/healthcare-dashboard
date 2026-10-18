import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

import { deletePatient, getPatient } from '../api/patients'
import type { Patient } from '../api/types'
import { AllergyBanner } from '../components/AllergyBanner'
import { ErrorMessage } from '../components/ErrorMessage'
import { NotesSection } from '../components/NotesSection'
import { ProfileCard } from '../components/ProfileCard'
import { StatusBadge } from '../components/StatusBadge'
import { SummaryPanel } from '../components/SummaryPanel'
import { formatDate, fullName } from '../format'

export function PatientDetailPage() {
  const { patientId = '' } = useParams()
  const { data, error, isPending, refetch } = useQuery({
    queryKey: ['patient', patientId],
    queryFn: () => getPatient(patientId),
  })

  return (
    <section>
      <p className="back-link">
        <Link to="/patients">← All patients</Link>
      </p>
      {data ? (
        <>
          {/* Keep the chart, and any note being typed, when a background refresh fails. */}
          {error && <ErrorMessage error={error} onRetry={() => refetch()} />}
          <Chart patient={data} />
        </>
      ) : isPending ? (
        <p className="muted">Loading patient…</p>
      ) : (
        <ErrorMessage error={error} onRetry={() => refetch()} />
      )}
    </section>
  )
}

function Chart({ patient }: { patient: Patient }) {
  // No date of death is stored, so an age for a deceased patient would keep counting up.
  const ageLine =
    patient.status === 'deceased'
      ? `Born ${formatDate(patient.date_of_birth)}`
      : `${patient.age} years old · Born ${formatDate(patient.date_of_birth)}`

  return (
    <>
      <header className="chart-header">
        <div className="chart-title">
          <h1>{fullName(patient)}</h1>
          <StatusBadge status={patient.status} />
          <div className="chart-actions">
            <Link to={`/patients/${patient.id}/edit`} className="button">
              Edit patient
            </Link>
          </div>
        </div>
        <p className="muted">{ageLine}</p>
        <AllergyBanner allergies={patient.allergies} />
      </header>
      <div className="chart-layout">
        <ProfileCard patient={patient} />
        <div className="chart-main">
          <SummaryPanel patientId={patient.id} />
          <NotesSection patientId={patient.id} />
        </div>
      </div>
      <DeletePatient patient={patient} />
    </>
  )
}

/**
 * Deleting is kept at the bottom of the chart, away from everyday actions, and asks first.
 * The API keeps the record (a soft delete), but nothing in the dashboard can bring it back.
 */
function DeletePatient({ patient }: { patient: Patient }) {
  const [confirming, setConfirming] = useState(false)
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const mutation = useMutation({
    mutationFn: () => deletePatient(patient.id),
    onSuccess: async () => {
      navigate('/patients')
      queryClient.removeQueries({ queryKey: ['patient', patient.id] })
      await queryClient.invalidateQueries({ queryKey: ['patients'] })
    },
  })

  return (
    <section className="danger-zone" aria-label="Delete patient">
      {confirming ? (
        <div className="confirm" role="group" aria-label="Confirm deleting this patient">
          <span>
            Delete {fullName(patient)}? Their chart and notes will no longer appear in the
            dashboard, and this can't be undone here.
          </span>
          <button
            type="button"
            className="button button-danger"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? 'Deleting…' : 'Delete patient'}
          </button>
          <button
            type="button"
            className="button"
            disabled={mutation.isPending}
            onClick={() => {
              setConfirming(false)
              mutation.reset()
            }}
          >
            Cancel
          </button>
        </div>
      ) : (
        <button type="button" className="link-button" onClick={() => setConfirming(true)}>
          Delete patient
        </button>
      )}
      {mutation.error && <ErrorMessage error={mutation.error} />}
    </section>
  )
}
