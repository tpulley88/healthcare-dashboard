import { describe, expect, it } from 'vitest'

import {
  conditionsPreview,
  formatDate,
  formatDateTime,
  localDateTimeNow,
  summaryCoverage,
  withLocalOffset,
} from './format'

// Vitest sets TZ for the whole run (see vite.config.ts), so these results are predictable.

describe('formatDate', () => {
  it('shows the calendar date as written, with no timezone shift', () => {
    expect(formatDate('1958-03-02')).toBe('Mar 2, 1958')
    expect(formatDate('2026-01-01')).toBe('Jan 1, 2026')
  })

  it('shows a dash for a missing date', () => {
    expect(formatDate(null)).toBe('—')
  })
})

describe('formatDateTime', () => {
  it('shows local time with the zone name', () => {
    expect(formatDateTime('2026-09-21T20:45:00Z')).toBe('Sep 21, 2026, 4:45 PM EDT')
    expect(formatDateTime('2026-01-15T14:00:00Z')).toBe('Jan 15, 2026, 9:00 AM EST')
  })

  it('shows the local date when it differs from the UTC date', () => {
    expect(formatDateTime('2026-10-18T02:00:00Z')).toBe('Oct 17, 2026, 10:00 PM EDT')
  })
})

describe('withLocalOffset', () => {
  it('uses the offset in effect on that date', () => {
    expect(withLocalOffset('2026-09-20T09:30')).toBe('2026-09-20T09:30:00-04:00')
    expect(withLocalOffset('2026-01-15T09:30')).toBe('2026-01-15T09:30:00-05:00')
  })
})

describe('localDateTimeNow', () => {
  it('formats local time for a datetime-local input', () => {
    expect(localDateTimeNow(new Date('2026-10-18T02:05:00Z'))).toBe('2026-10-17T22:05')
  })
})

describe('summaryCoverage', () => {
  it('says how many notes the summary covers, then over which dates', () => {
    expect(
      summaryCoverage({
        notes_included: 10,
        notes_total: 14,
        notes_from: '2025-06-16',
        notes_to: '2026-03-09',
      }),
    ).toEqual({
      scope: 'Not a complete clinical history · Summary of the latest 10 of 14 notes',
      span: 'Jun 16, 2025 – Mar 9, 2026',
    })
    expect(
      summaryCoverage({
        notes_included: 1,
        notes_total: 1,
        notes_from: '2026-03-09',
        notes_to: '2026-03-09',
      }),
    ).toEqual({ scope: 'Not a complete clinical history · Summary of 1 note', span: 'Mar 9, 2026' })
  })

  it('says when there are no notes', () => {
    expect(
      summaryCoverage({ notes_included: 0, notes_total: 0, notes_from: null, notes_to: null }),
    ).toEqual({ scope: 'No notes yet', span: null })
  })
})

describe('conditionsPreview', () => {
  it('lists up to two conditions, then counts the rest', () => {
    expect(conditionsPreview(['Asthma'])).toBe('Asthma')
    expect(conditionsPreview(['Asthma', 'COPD'])).toBe('Asthma, COPD')
    expect(conditionsPreview(['Asthma', 'COPD', 'Hypertension'])).toBe('Asthma, COPD +1 more')
  })

  it('keeps unknown distinct from none known', () => {
    expect(conditionsPreview(null)).toBe('Unknown')
    expect(conditionsPreview([])).toBe('None known')
  })
})
