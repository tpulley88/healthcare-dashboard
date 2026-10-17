import { request } from './client'
import type { Patient, PatientListParams, PatientPage } from './types'

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
