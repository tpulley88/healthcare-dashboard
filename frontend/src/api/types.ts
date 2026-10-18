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

/**
 * The fields staff can set when creating or editing a patient.
 * Optional fields are null when blank. On an edit, send only the fields that changed.
 */
export type PatientInput = Pick<
  Patient,
  | 'first_name'
  | 'last_name'
  | 'date_of_birth'
  | 'phone'
  | 'email'
  | 'street'
  | 'city'
  | 'state'
  | 'postal_code'
  | 'blood_type'
  | 'allergies'
  | 'conditions'
  | 'status'
  | 'last_visit_date'
>

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

export interface Note {
  id: string
  patient_id: string
  /** When the care happened, as an ISO timestamp in UTC. */
  taken_at: string
  content: string
  /** When the note was saved. */
  created_at: string
}

export interface NoteCreate {
  /** Must include a UTC offset, for example 2026-09-20T09:30:00-04:00. */
  taken_at: string
  content: string
}

/**
 * The narrative covers only the most recent notes, using the opening of each one.
 * The notes_* fields say how much of the chart it reflects.
 */
export interface PatientSummary {
  patient_id: string
  name: string
  age: number
  date_of_birth: string
  blood_type: BloodType | null
  status: PatientStatus
  conditions: string[] | null
  allergies: string[] | null
  headline: string
  narrative: string
  notes_included: number
  notes_total: number
  /** Practice-local dates of the first and last notes included; null when there are none. */
  notes_from: string | null
  notes_to: string | null
  source: 'template'
}
