import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'

import { listPatients } from '../api/patients'
import type { PatientListParams, PatientPage, PatientStatus, SortField } from '../api/types'
import { ErrorMessage } from '../components/ErrorMessage'
import { StatusBadge } from '../components/StatusBadge'
import { conditionsPreview, formatDate, STATUS_LABELS } from '../format'
import { readListParams, writeListParams } from './listParams'

const SEARCH_DELAY_MS = 300

export function PatientListPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const params = readListParams(searchParams)

  const { data, error, isPending, isFetching, refetch } = useQuery({
    queryKey: ['patients', params],
    queryFn: () => listPatients(params),
    // Keep showing the current page while the next one loads, instead of flashing empty.
    placeholderData: keepPreviousData,
  })

  const update = (changes: Partial<Omit<PatientListParams, 'pageSize'>>) =>
    setSearchParams(writeListParams(params, changes))

  return (
    <section>
      <div className="page-header">
        <h1>Patients</h1>
      </div>

      <div className="toolbar">
        <SearchBox value={params.search} onSearch={(search) => update({ search })} />
        <label className="field-inline">
          Status
          <select
            value={params.status ?? ''}
            onChange={(event) =>
              update({ status: (event.target.value || null) as PatientStatus | null })
            }
          >
            <option value="">All</option>
            {Object.entries(STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {isPending ? (
        <p className="muted">Loading patients…</p>
      ) : error && !data ? (
        <ErrorMessage error={error} onRetry={() => refetch()} />
      ) : data ? (
        <>
          {error && <ErrorMessage error={error} onRetry={() => refetch()} />}
          <PatientTable
            page={data}
            params={params}
            busy={isFetching}
            onSort={(sort) =>
              update({
                sort,
                order: sort === params.sort && params.order === 'asc' ? 'desc' : 'asc',
              })
            }
          />
          <Pagination
            page={params.page}
            pageSize={params.pageSize}
            total={data.total}
            onPage={(page) => update({ page })}
          />
        </>
      ) : null}
    </section>
  )
}

/** Updates the search after typing pauses, so each keystroke doesn't send a request. */
function SearchBox({ value, onSearch }: { value: string; onSearch: (value: string) => void }) {
  const [text, setText] = useState(value)
  const [lastValue, setLastValue] = useState(value)

  // Follow the URL when it changes from outside, such as the Back button.
  if (value !== lastValue) {
    setLastValue(value)
    setText(value)
  }

  useEffect(() => {
    if (text === value) return
    const timer = setTimeout(() => onSearch(text), SEARCH_DELAY_MS)
    return () => clearTimeout(timer)
  }, [text, value, onSearch])

  return (
    <label className="field-inline search">
      Search
      <input
        type="search"
        placeholder="Patient name"
        maxLength={100}
        value={text}
        onChange={(event) => setText(event.target.value)}
      />
    </label>
  )
}

function PatientTable({
  page,
  params,
  busy,
  onSort,
}: {
  page: PatientPage
  params: PatientListParams
  busy: boolean
  onSort: (field: SortField) => void
}) {
  const navigate = useNavigate()

  if (page.items.length === 0) {
    const filtered = params.search.trim() !== '' || params.status !== null
    return (
      <p className="empty">
        {page.total > 0
          ? 'This page is past the end of the list.'
          : filtered
            ? 'No patients match this search.'
            : 'No patients yet.'}
      </p>
    )
  }

  const sortHeader = (field: SortField, label: string) => {
    const active = params.sort === field
    return (
      <th
        key={field}
        scope="col"
        aria-sort={active ? (params.order === 'asc' ? 'ascending' : 'descending') : 'none'}
      >
        {/* Unsorted columns show a two-way arrow, so it's clear they can be sorted. */}
        <button
          type="button"
          className={active ? 'sort-button sort-button-active' : 'sort-button'}
          title={`Sort by ${label.toLowerCase()}`}
          onClick={() => onSort(field)}
        >
          {label}
          <span className="sort-icon" aria-hidden="true">
            {active ? (params.order === 'asc' ? '▲' : '▼') : '↕'}
          </span>
        </button>
      </th>
    )
  }

  return (
    <div className="table-wrap">
      <table className="data-table" aria-busy={busy}>
        <thead>
          <tr>
            {sortHeader('name', 'Name')}
            {sortHeader('age', 'Age')}
            <th scope="col" className="secondary-column">
              Date of birth
            </th>
            <th scope="col">Status</th>
            <th scope="col">Allergies</th>
            <th scope="col" className="secondary-column">
              Conditions
            </th>
            {sortHeader('last_visit_date', 'Last visit')}
            <th scope="col" className="secondary-column">
              Phone
            </th>
          </tr>
        </thead>
        <tbody>
          {page.items.map((patient) => (
            <tr
              key={patient.id}
              className="clickable-row"
              onClick={(event) => {
                // The name link handles its own clicks, including Cmd-click for a new tab.
                if ((event.target as HTMLElement).closest('a')) return
                // Selecting text in a row, such as a phone number, shouldn't open the patient.
                if (window.getSelection()?.toString()) return
                navigate(`/patients/${patient.id}`)
              }}
            >
              <td>
                {/* A real link, so keyboard and screen reader users can open the patient too. */}
                <Link to={`/patients/${patient.id}`} className="row-link">
                  {`${patient.last_name}, ${patient.first_name}`}
                </Link>
              </td>
              <td>{patient.age}</td>
              <td className="secondary-column">{formatDate(patient.date_of_birth)}</td>
              <td>
                <StatusBadge status={patient.status} />
              </td>
              <AllergyCell allergies={patient.allergies} />
              <ConditionsCell conditions={patient.conditions} />
              <td>{formatDate(patient.last_visit_date)}</td>
              <td className="secondary-column">{patient.phone ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/**
 * A red dot when allergies are recorded, with the list in the tooltip and in hidden text for
 * screen readers. An empty cell could be misread as "no allergies", so the other two states
 * are spelled out: NKA (no known allergies) and Unknown.
 */
function AllergyCell({ allergies }: { allergies: string[] | null }) {
  if (allergies === null) return <td className="muted">Unknown</td>
  if (allergies.length === 0) {
    return (
      <td className="muted">
        <abbr title="No known allergies">NKA</abbr>
      </td>
    )
  }
  const text = `Allergies: ${allergies.join(', ')}`
  return (
    <td title={text}>
      <span className="allergy-marker" aria-hidden="true" />
      <span className="visually-hidden">{text}</span>
    </td>
  )
}

/** A short preview for scanning the list. The full list is in the tooltip and the chart. */
function ConditionsCell({ conditions }: { conditions: string[] | null }) {
  const preview = conditionsPreview(conditions)
  const empty = conditions === null || conditions.length === 0
  return (
    <td
      className={`conditions secondary-column${empty ? ' muted' : ''}`}
      title={conditions?.join(', ')}
    >
      {preview}
    </td>
  )
}

function Pagination({
  page,
  pageSize,
  total,
  onPage,
}: {
  page: number
  pageSize: number
  total: number
  onPage: (page: number) => void
}) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize))
  const first = total === 0 ? 0 : Math.min((page - 1) * pageSize + 1, total)
  const last = Math.min(page * pageSize, total)
  return (
    <nav className="pagination" aria-label="Pages">
      <p aria-live="polite">
        {total === 0 ? 'No results' : `Showing ${first}–${last} of ${total} patients`}
      </p>
      <div className="pagination-buttons">
        <button
          type="button"
          className="button"
          disabled={page <= 1}
          onClick={() => onPage(Math.min(page - 1, pageCount))}
        >
          Previous
        </button>
        <span>
          Page {Math.min(page, pageCount)} of {pageCount}
        </span>
        <button
          type="button"
          className="button"
          disabled={page >= pageCount}
          onClick={() => onPage(page + 1)}
        >
          Next
        </button>
      </div>
    </nav>
  )
}
