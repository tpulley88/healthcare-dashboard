import type { Patient, PatientStatus, PatientSummary } from './api/types'

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

const DATE_TIME = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
  timeZoneName: 'short',
})

/**
 * Format a timestamp in the browser's timezone, with the zone name: "Sep 20, 2026, 9:30 AM EDT".
 * The zone name makes the time unambiguous for anyone viewing from outside the practice.
 */
export function formatDateTime(value: string): string {
  return DATE_TIME.format(new Date(value))
}

const pad = (n: number) => String(n).padStart(2, '0')

/** The current local time in the "YYYY-MM-DDTHH:mm" form a datetime-local input expects. */
export function localDateTimeNow(now = new Date()): string {
  return (
    `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}` +
    `T${pad(now.getHours())}:${pad(now.getMinutes())}`
  )
}

/**
 * Add the browser's UTC offset to a datetime-local value: "2026-09-20T09:30" becomes
 * "2026-09-20T09:30:00-04:00". The offset is the one in effect on that date,
 * so a note dated in winter gets the standard-time offset even if it's entered in summer.
 */
export function withLocalOffset(localValue: string): string {
  // A date-time string without an offset is read as local time.
  const minutesEast = -new Date(localValue).getTimezoneOffset()
  const sign = minutesEast >= 0 ? '+' : '-'
  const abs = Math.abs(minutesEast)
  return `${localValue}:00${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`
}

/**
 * What the summary covers, shown above it on two lines:
 * "Not a complete clinical history · Summary of the latest 10 of 14 notes" and
 * "Jun 16, 2025 – Mar 9, 2026". With no notes there's no date range.
 */
export function summaryCoverage(
  summary: Pick<PatientSummary, 'notes_included' | 'notes_total' | 'notes_from' | 'notes_to'>,
): { scope: string; span: string | null } {
  const { notes_included: included, notes_total: total, notes_from: from, notes_to: to } = summary
  if (total === 0 || !from || !to) return { scope: 'No notes yet', span: null }
  const count =
    included === total
      ? `${total} ${total === 1 ? 'note' : 'notes'}`
      : `the latest ${included} of ${total} notes`
  return {
    scope: `Not a complete clinical history · Summary of ${count}`,
    span: from === to ? formatDate(from) : `${formatDate(from)} – ${formatDate(to)}`,
  }
}

/**
 * Conditions for the patient list: up to `shown`, then "+N more".
 * Unknown (null) and none known (an empty list) read differently, as they do everywhere else.
 */
export function conditionsPreview(conditions: string[] | null, shown = 2): string {
  if (conditions === null) return 'Unknown'
  if (conditions.length === 0) return 'None known'
  const extra = conditions.length - shown
  const listed = conditions.slice(0, shown).join(', ')
  return extra > 0 ? `${listed} +${extra} more` : listed
}
