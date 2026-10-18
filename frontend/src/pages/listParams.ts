import type { PatientListParams, PatientStatus, SortField } from '../api/types'

export const PAGE_SIZE = 20

const STATUSES: readonly PatientStatus[] = ['active', 'inactive', 'deceased']
const SORT_FIELDS: readonly SortField[] = ['name', 'age', 'last_visit_date', 'created_at']

function oneOf<T extends string>(allowed: readonly T[], value: string | null): T | null {
  return allowed.find((item) => item === value) ?? null
}

/**
 * Read the list's search, filter, sort, and page from the URL.
 *
 * The URL is the source of truth, so Back, refresh, and shared links keep the same view.
 * Values someone typed into the URL by hand that the API would reject fall back to defaults
 * instead of showing an error page.
 */
export function readListParams(url: URLSearchParams): PatientListParams {
  const page = Number(url.get('page'))
  return {
    page: Number.isInteger(page) && page >= 1 ? page : 1,
    pageSize: PAGE_SIZE,
    search: (url.get('search') ?? '').slice(0, 100),
    status: oneOf(STATUSES, url.get('status')),
    sort: oneOf(SORT_FIELDS, url.get('sort')) ?? 'name',
    order: url.get('order') === 'desc' ? 'desc' : 'asc',
  }
}

/**
 * Write list settings back to the URL, leaving out defaults to keep links short.
 * Any change other than the page itself returns to page 1, since the old page may not exist.
 */
export function writeListParams(
  current: PatientListParams,
  changes: Partial<Omit<PatientListParams, 'pageSize'>>,
): URLSearchParams {
  const next = { ...current, ...changes }
  if (!('page' in changes)) next.page = 1

  const url = new URLSearchParams()
  if (next.search.trim()) url.set('search', next.search.trim())
  if (next.status) url.set('status', next.status)
  if (next.sort !== 'name') url.set('sort', next.sort)
  if (next.order !== 'asc') url.set('order', next.order)
  if (next.page > 1) url.set('page', String(next.page))
  return url
}
