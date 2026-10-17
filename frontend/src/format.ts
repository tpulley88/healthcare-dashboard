import type { Patient, PatientStatus } from './api/types'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/**
 * Format a "YYYY-MM-DD" date as "Mar 2, 1958".
 *
 * The string is split rather than passed to `new Date()`, which would read it as UTC midnight
 * and show the previous day in any timezone west of UTC.
 */
export function formatDate(value: string | null): string {
  if (!value) return '—'
  const [year, month, day] = value.split('-').map(Number)
  if (!year || !month || !day) return value
  return `${MONTHS[month - 1]} ${day}, ${year}`
}

export function fullName(patient: Pick<Patient, 'first_name' | 'last_name'>): string {
  return `${patient.first_name} ${patient.last_name}`
}

export const STATUS_LABELS: Record<PatientStatus, string> = {
  active: 'Active',
  inactive: 'Inactive',
  deceased: 'Deceased',
}
