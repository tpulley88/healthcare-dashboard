import { useQueries, useQuery } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'

import { listPatients } from '../api/patients'
import type { PatientListParams, PatientStatus } from '../api/types'
import { ErrorMessage } from '../components/ErrorMessage'
import { StatusBadge } from '../components/StatusBadge'
import { STATUS_LABELS, formatDate, fullName } from '../format'

const RECENT_COUNT = 5

const STATUSES: PatientStatus[] = ['active', 'inactive', 'deceased']

function listQuery(changes: Partial<PatientListParams>): PatientListParams {
  return { page: 1, pageSize: 1, search: '', status: null, sort: 'name', order: 'asc', ...changes }
}

/**
 * The home page: finding a patient, patient counts by status, and the most recent visits.
 *
 * Counts come from the list endpoint's `total` with a page size of 1,
 * so no separate statistics endpoint is needed.
 */
export function DashboardPage() {
  const counts = useQueries({
    queries: STATUSES.map((status) => {
      const params = listQuery({ status })
      return { queryKey: ['patients', params], queryFn: () => listPatients(params) }
    }),
  })
  const recentParams = listQuery({
    pageSize: RECENT_COUNT,
    sort: 'last_visit_date',
    order: 'desc',
  })
  const recent = useQuery({
    queryKey: ['patients', recentParams],
    queryFn: () => listPatients(recentParams),
  })

  const countError = counts.find((query) => query.error)?.error
  const total = counts.every((query) => query.data)
    ? counts.reduce((sum, query) => sum + (query.data?.total ?? 0), 0)
    : null

  return (
    <section>
      <div className="page-header">
        <h1>Dashboard</h1>
      </div>

      <FindPatient />

      {/* Counts already loaded stay on screen if a background refresh fails. */}
      {countError && (
        <ErrorMessage error={countError} onRetry={() => counts.forEach((q) => q.refetch())} />
      )}
      {(!countError || counts.every((query) => query.data)) && (
        <ul className="stat-grid" aria-label="Patients by status">
          <StatCard label="All patients" value={total} to="/patients" />
          {STATUSES.map((status, index) => (
            <StatCard
              key={status}
              label={STATUS_LABELS[status]}
              value={counts[index].data?.total ?? null}
              to={`/patients?status=${status}`}
            />
          ))}
        </ul>
      )}

      <section className="card" aria-labelledby="recent-heading">
        <h2 id="recent-heading">Patients with recent visits</h2>
        {recent.isPending ? (
          <p className="muted">Loading…</p>
        ) : !recent.data ? (
          <ErrorMessage error={recent.error} onRetry={() => recent.refetch()} />
        ) : (
          <>
            {recent.error && <ErrorMessage error={recent.error} onRetry={() => recent.refetch()} />}
            {recent.data.items.length === 0 ? (
              <p className="muted">No visits recorded yet.</p>
            ) : (
              <ul className="recent-list">
                {recent.data.items.map((patient) => (
                  <li key={patient.id}>
                    <Link to={`/patients/${patient.id}`}>{fullName(patient)}</Link>
                    <span className="muted">Last visit {formatDate(patient.last_visit_date)}</span>
                    <StatusBadge status={patient.status} />
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
        <p className="small">
          <Link to="/patients?sort=last_visit_date&order=desc">See all by last visit</Link>
        </p>
      </section>
    </section>
  )
}

function StatCard({ label, value, to }: { label: string; value: number | null; to: string }) {
  return (
    <li>
      <Link to={to} className="stat-card">
        <span className="stat-value">{value ?? '…'}</span>
        <span className="stat-label">{label}</span>
      </Link>
    </li>
  )
}

/** Opens the patient list already searched, where filters, sorting, and paging are available. */
function FindPatient() {
  const [name, setName] = useState('')
  const navigate = useNavigate()

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const search = name.trim()
    navigate(search ? `/patients?${new URLSearchParams({ search })}` : '/patients')
  }

  return (
    <form className="find-patient card" role="search" onSubmit={submit}>
      <label htmlFor="find-patient">Find a patient</label>
      <div className="find-patient-row">
        <input
          id="find-patient"
          type="search"
          placeholder="Name"
          maxLength={100}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <button type="submit" className="button button-primary">
          Search
        </button>
      </div>
    </form>
  )
}
