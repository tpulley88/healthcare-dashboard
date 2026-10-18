import type { Patient } from '../api/types'
import { formatDate } from '../format'

function clinicalList(items: string[] | null, noneKnown: string): string {
  if (items === null) return 'Unknown'
  return items.length === 0 ? noneKnown : items.join(', ')
}

function address(patient: Patient): string | null {
  const cityLine = [patient.city, [patient.state, patient.postal_code].filter(Boolean).join(' ')]
    .filter(Boolean)
    .join(', ')
  return [patient.street, cityLine].filter(Boolean).join('\n') || null
}

export function ProfileCard({ patient }: { patient: Patient }) {
  const rows: [string, string | null][] = [
    ['Blood type', patient.blood_type],
    ['Conditions', clinicalList(patient.conditions, 'No known chronic conditions')],
    ['Last visit', patient.last_visit_date && formatDate(patient.last_visit_date)],
    ['Phone', patient.phone],
    ['Email', patient.email],
    ['Address', address(patient)],
  ]
  return (
    <section className="card" aria-labelledby="profile-heading">
      <h2 id="profile-heading">Profile</h2>
      <dl className="details">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value ?? <span className="muted">Not recorded</span>}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}
