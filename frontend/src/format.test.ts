import { describe, expect, it } from 'vitest'

import { formatDate } from './format'

describe('formatDate', () => {
  it('shows the calendar date as written, with no timezone shift', () => {
    expect(formatDate('1958-03-02')).toBe('Mar 2, 1958')
    expect(formatDate('2026-01-01')).toBe('Jan 1, 2026')
  })

  it('shows a dash for a missing date', () => {
    expect(formatDate(null)).toBe('—')
  })
})
