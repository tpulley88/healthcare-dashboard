/**
 * Shapes returned by the API. They mirror the backend's Pydantic response models.
 *
 * Dates without a time (date_of_birth, last_visit_date) are "YYYY-MM-DD" strings.
 * For allergies and conditions, null means "unknown" and an empty list means "none known".
 */

export type PatientStatus = 'active' | 'inactive' | 'deceased'

export type BloodType = 'A+' | 'A-' | 'B+' | 'B-' | 'AB+' | 'AB-' | 'O+' | 'O-'

export interface Patient {
  id: string
  first_name: string
  last_name: string
  date_of_birth: string
  age: number
  phone: string | null
  email: string | null
  street: string | null
  city: string | null
  state: string | null
  postal_code: string | null
  blood_type: BloodType | null
  allergies: string[] | null
  conditions: string[] | null
  status: PatientStatus
  last_visit_date: string | null
  created_at: string
  updated_at: string
  /** Goes up on every save. Sent back as If-Match so an outdated save is rejected. */
  version: number
}

export interface PatientPage {
  items: Patient[]
  /** Every matching patient, not just this page. */
  total: number
  page: number
  page_size: number
}

export type SortField = 'name' | 'age' | 'last_visit_date' | 'created_at'
export type SortOrder = 'asc' | 'desc'

export interface PatientListParams {
  page: number
  pageSize: number
  search: string
  status: PatientStatus | null
  sort: SortField
  order: SortOrder
}
