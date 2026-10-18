import { request } from './client'
import type { Patient, PatientInput, PatientListParams, PatientPage } from './types'

const JSON_HEADERS = { 'Content-Type': 'application/json' }

export function listPatients(params: PatientListParams): Promise<PatientPage> {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
    sort: params.sort,
    order: params.order,
  })
  if (params.search.trim()) query.set('search', params.search.trim())
  if (params.status) query.set('status', params.status)
  return request(`/patients?${query}`)
}

export function getPatient(id: string): Promise<Patient> {
  return request(`/patients/${encodeURIComponent(id)}`)
}

export function createPatient(input: PatientInput): Promise<Patient> {
  return request('/patients', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify(input),
  })
}

/**
 * Save changes to a patient.
 *
 * `version` is the version the edit started from. If anyone has saved the patient since,
 * the API refuses with a 412 instead of overwriting their changes.
 */
export function updatePatient(
  id: string,
  changes: Partial<PatientInput>,
  version: number,
): Promise<Patient> {
  return request(`/patients/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { ...JSON_HEADERS, 'If-Match': `"${version}"` },
    body: JSON.stringify(changes),
  })
}

export function deletePatient(id: string): Promise<void> {
  return request(`/patients/${encodeURIComponent(id)}`, { method: 'DELETE' })
}
