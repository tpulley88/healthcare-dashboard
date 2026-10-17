import { describe, expect, it } from 'vitest'

import { readListParams, writeListParams } from './listParams'

const read = (query: string) => readListParams(new URLSearchParams(query))

describe('readListParams', () => {
  it('uses defaults for an empty URL', () => {
    expect(read('')).toEqual({
      page: 1,
      pageSize: 20,
      search: '',
      status: null,
      sort: 'name',
      order: 'asc',
    })
  })

  it('reads valid values', () => {
    expect(read('page=3&search=ana&status=inactive&sort=age&order=desc')).toMatchObject({
      page: 3,
      search: 'ana',
      status: 'inactive',
      sort: 'age',
      order: 'desc',
    })
  })

  it('falls back to defaults for values the API would reject', () => {
    expect(read('page=-2&status=asleep&sort=height&order=sideways')).toMatchObject({
      page: 1,
      status: null,
      sort: 'name',
      order: 'asc',
    })
    expect(read('page=1.5').page).toBe(1)
    expect(read(`search=${'x'.repeat(150)}`).search).toHaveLength(100)
  })
})

describe('writeListParams', () => {
  const current = read('search=ana&status=active&sort=age&order=desc&page=4')

  it('returns to page 1 when the search, filter, or sort changes', () => {
    expect(writeListParams(current, { status: 'inactive' }).get('page')).toBeNull()
    expect(writeListParams(current, { search: 'bo' }).get('page')).toBeNull()
  })

  it('keeps the other settings when only the page changes', () => {
    expect(writeListParams(current, { page: 5 }).toString()).toBe(
      'search=ana&status=active&sort=age&order=desc&page=5',
    )
  })

  it('leaves defaults out of the URL', () => {
    expect(writeListParams(read(''), { page: 1 }).toString()).toBe('')
  })
})
