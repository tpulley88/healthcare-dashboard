/**
 * What the patient form holds, and how it turns into API requests.
 *
 * The form keeps every field as text while staff type, so a half-typed value is never lost.
 * `toPatientInput` converts it to the API's shape: trimmed, with blanks as null.
 * Comparing two inputs field by field tells an edit which fields to send,
 * and, after a conflicting save, which fields each person changed.
 */

import type { BloodType, Patient, PatientInput, PatientStatus } from '../api/types'
import { STATUS_LABELS, formatDate } from '../format'

/**
 * Allergies and conditions are recorded in one of three ways:
 * not asked yet (unknown), asked with nothing found (none known), or a list of entries.
 */
export type ListMode = 'unknown' | 'none' | 'has'

/**
 * `text` holds one entry per line.
 * It is kept while another mode is chosen, so switching back restores it.
 * Only the mode chosen at save time is sent.
 */
export interface ListValue {
  mode: ListMode
  text: string
}

export interface PatientFormValues {
  first_name: string
  last_name: string
  date_of_birth: string
  phone: string
  email: string
  street: string
  city: string
  state: string
  postal_code: string
  blood_type: BloodType | ''
  allergies: ListValue
  conditions: ListValue
  status: PatientStatus
  last_visit_date: string
}

export type PatientField = keyof PatientInput

/** Every editable field, in the order the form shows them, with its label. */
export const FIELD_LABELS: Record<PatientField, string> = {
  first_name: 'First name',
  last_name: 'Last name',
  date_of_birth: 'Date of birth',
  status: 'Status',
  allergies: 'Allergies',
  conditions: 'Conditions',
  blood_type: 'Blood type',
  last_visit_date: 'Last visit',
  phone: 'Phone',
  email: 'Email',
  street: 'Street',
  city: 'City',
  state: 'State',
  postal_code: 'ZIP code',
}

const FIELDS = Object.keys(FIELD_LABELS) as PatientField[]

export const MAX_LIST_ENTRIES = 50

export function emptyValues(): PatientFormValues {
  return {
    first_name: '',
    last_name: '',
    date_of_birth: '',
    phone: '',
    email: '',
    street: '',
    city: '',
    state: '',
    postal_code: '',
    blood_type: '',
    allergies: { mode: 'unknown', text: '' },
    conditions: { mode: 'unknown', text: '' },
    status: 'active',
    last_visit_date: '',
  }
}

function listValue(items: string[] | null): ListValue {
  if (items === null) return { mode: 'unknown', text: '' }
  return { mode: items.length === 0 ? 'none' : 'has', text: items.join('\n') }
}

export function valuesFromPatient(patient: Patient): PatientFormValues {
  return {
    first_name: patient.first_name,
    last_name: patient.last_name,
    date_of_birth: patient.date_of_birth,
    phone: patient.phone ?? '',
    email: patient.email ?? '',
    street: patient.street ?? '',
    city: patient.city ?? '',
    state: patient.state ?? '',
    postal_code: patient.postal_code ?? '',
    blood_type: patient.blood_type ?? '',
    allergies: listValue(patient.allergies),
    conditions: listValue(patient.conditions),
    status: patient.status,
    last_visit_date: patient.last_visit_date ?? '',
  }
}

/** The entries typed into a list, one per line, ignoring blank lines. */
export function listEntries(text: string): string[] {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
}

function toList(value: ListValue): string[] | null {
  if (value.mode === 'unknown') return null
  return value.mode === 'none' ? [] : listEntries(value.text)
}

function blankToNull(value: string): string | null {
  return value.trim() || null
}

export function toPatientInput(values: PatientFormValues): PatientInput {
  return {
    first_name: values.first_name.trim(),
    last_name: values.last_name.trim(),
    date_of_birth: values.date_of_birth,
    phone: blankToNull(values.phone),
    email: blankToNull(values.email),
    street: blankToNull(values.street),
    city: blankToNull(values.city),
    state: values.state || null,
    postal_code: blankToNull(values.postal_code),
    blood_type: values.blood_type || null,
    allergies: toList(values.allergies),
    conditions: toList(values.conditions),
    status: values.status,
    last_visit_date: values.last_visit_date || null,
  }
}

export function inputFromPatient(patient: Patient): PatientInput {
  return toPatientInput(valuesFromPatient(patient))
}

/** The fields whose values differ between two versions, in form order. */
export function changedFields(before: PatientInput, after: PatientInput): PatientField[] {
  // JSON comparison treats lists as equal only when they hold the same entries in the same order.
  return FIELDS.filter((field) => JSON.stringify(before[field]) !== JSON.stringify(after[field]))
}

/** Only the given fields, ready to send as an edit. */
export function pickFields(input: PatientInput, fields: PatientField[]): Partial<PatientInput> {
  return Object.fromEntries(fields.map((field) => [field, input[field]]))
}

/**
 * Checks done before sending, for mistakes the form can catch on its own.
 * The API validates everything again and its messages are shown the same way.
 */
export function checkValues(values: PatientFormValues): Partial<Record<PatientField, string>> {
  const errors: Partial<Record<PatientField, string>> = {}
  if (!values.first_name.trim()) errors.first_name = 'Enter a first name'
  if (!values.last_name.trim()) errors.last_name = 'Enter a last name'
  if (!values.date_of_birth) errors.date_of_birth = 'Enter a date of birth'
  for (const field of ['allergies', 'conditions'] as const) {
    const value = values[field]
    if (value.mode !== 'has') continue
    const count = listEntries(value.text).length
    if (count === 0) {
      errors[field] = 'Enter at least one, or choose "None known" or "Unknown"'
    } else if (count > MAX_LIST_ENTRIES) {
      errors[field] = `Enter at most ${MAX_LIST_ENTRIES}`
    }
  }
  return errors
}

/**
 * Apply this person's edits on top of the latest saved patient.
 *
 * Used after someone else saved first. Fields only they changed take their new value,
 * and fields this person changed keep this person's value.
 */
export function rebaseValues(
  latest: Patient,
  values: PatientFormValues,
  mine: PatientField[],
): PatientFormValues {
  const rebased = valuesFromPatient(latest)
  for (const field of mine) {
    // Both objects have the same shape, so copying one field across is safe.
    ;(rebased as unknown as Record<string, unknown>)[field] = values[field]
  }
  return rebased
}

/** The two-letter codes the API accepts: the 50 states plus DC. */
export const US_STATES = (
  'AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH ' +
  'NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'
).split(' ')

export const BLOOD_TYPES: BloodType[] = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']

/** A field's saved value as staff would read it, for comparing two versions side by side. */
export function displayValue(input: PatientInput, field: PatientField): string {
  const value = input[field]
  if (field === 'allergies' || field === 'conditions') {
    const items = value as string[] | null
    if (items === null) return 'Unknown'
    return items.length === 0 ? 'None known' : items.join(', ')
  }
  if (value === null) return 'Blank'
  if (field === 'status') return STATUS_LABELS[value as PatientStatus]
  if (field === 'date_of_birth' || field === 'last_visit_date') return formatDate(value as string)
  return value as string
}
