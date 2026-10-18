import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'

import { getPatient } from '../api/patients'
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
      {isPending ? (
        <p className="muted">Loading patient…</p>
      ) : error ? (
        <ErrorMessage error={error} onRetry={() => refetch()} />
      ) : (
        <Chart patient={data} />
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
    </>
  )
}
