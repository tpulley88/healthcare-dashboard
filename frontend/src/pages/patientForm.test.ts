import { describe, expect, it } from 'vitest'

import type { Patient } from '../api/types'
import {
  changedFields,
  checkValues,
  displayValue,
  emptyValues,
  inputFromPatient,
  pickFields,
  rebaseValues,
  toPatientInput,
  valuesFromPatient,
} from './patientForm'

const patient: Patient = {
  id: '6f1c2b1e-0000-4000-8000-000000000001',
  first_name: 'Ana',
  last_name: 'Ruiz',
  date_of_birth: '1958-03-02',
  age: 68,
  phone: '(617) 555-0123',
  email: null,
  street: null,
  city: 'Boston',
  state: 'MA',
  postal_code: null,
  blood_type: 'O+',
  allergies: ['Penicillin', 'Latex'],
  conditions: [],
  status: 'active',
  last_visit_date: '2026-09-20',
  created_at: '2026-01-01T12:00:00Z',
  updated_at: '2026-09-20T12:00:00Z',
  version: 3,
}

describe('toPatientInput', () => {
  it('trims text and sends blanks as null', () => {
    const values = {
      ...emptyValues(),
      first_name: '  Ana ',
      last_name: 'Ruiz',
      date_of_birth: '1958-03-02',
      city: '   ',
      phone: ' 617-555-0123 ',
    }
    expect(toPatientInput(values)).toMatchObject({
      first_name: 'Ana',
      city: null,
      phone: '617-555-0123',
      state: null,
      blood_type: null,
      last_visit_date: null,
    })
  })

  it('sends the three list choices as null, an empty list, or the entries', () => {
    const input = toPatientInput({
      ...emptyValues(),
      allergies: { mode: 'has', text: ' Penicillin \n\n Latex\n' },
      conditions: { mode: 'none', text: 'Asthma' },
    })
    expect(input.allergies).toEqual(['Penicillin', 'Latex'])
    // Text left behind from an earlier choice isn't sent.
    expect(input.conditions).toEqual([])
    expect(toPatientInput(emptyValues()).allergies).toBeNull()
  })
})

describe('valuesFromPatient', () => {
  it('round-trips a stored patient without reporting changes', () => {
    expect(
      changedFields(inputFromPatient(patient), toPatientInput(valuesFromPatient(patient))),
    ).toEqual([])
  })

  it('shows each list choice', () => {
    const values = valuesFromPatient({ ...patient, conditions: null })
    expect(values.allergies).toEqual({ mode: 'has', text: 'Penicillin\nLatex' })
    expect(values.conditions.mode).toBe('unknown')
    expect(valuesFromPatient(patient).conditions.mode).toBe('none')
  })
})

describe('changedFields', () => {
  it('finds only the fields that differ, ignoring whitespace-only edits', () => {
    const values = {
      ...valuesFromPatient(patient),
      first_name: 'Ana ',
      city: '',
      allergies: { mode: 'has' as const, text: 'Latex\nPenicillin' },
    }
    const changed = changedFields(inputFromPatient(patient), toPatientInput(values))
    expect(changed).toEqual(['allergies', 'city'])
  })

  it('picks only those fields to send', () => {
    const input = toPatientInput({ ...valuesFromPatient(patient), city: '' })
    expect(pickFields(input, ['city'])).toEqual({ city: null })
  })
})

describe('checkValues', () => {
  it('requires names and date of birth', () => {
    expect(Object.keys(checkValues(emptyValues()))).toEqual([
      'first_name',
      'last_name',
      'date_of_birth',
    ])
  })

  it('blocks "has" with no entries, but not the other choices', () => {
    const values = {
      ...valuesFromPatient(patient),
      allergies: { mode: 'has' as const, text: ' \n ' },
      conditions: { mode: 'none' as const, text: '' },
    }
    expect(checkValues(values)).toEqual({
      allergies: 'Enter at least one, or choose "None known" or "Unknown"',
    })
  })

  it('limits list length to what the API accepts', () => {
    const text = Array.from({ length: 51 }, (_, i) => `Item ${i}`).join('\n')
    const values = { ...valuesFromPatient(patient), conditions: { mode: 'has' as const, text } }
    expect(checkValues(values).conditions).toBe('Enter at most 50')
  })
})

describe('rebaseValues', () => {
  it('keeps my edited fields and takes everything else from the latest save', () => {
    const latest = { ...patient, phone: '(617) 555-9999', city: 'Cambridge', version: 4 }
    const mine = { ...valuesFromPatient(patient), city: 'Somerville', email: 'ana@example.com' }
    const rebased = rebaseValues(latest, mine, ['city', 'email'])
    expect(rebased.phone).toBe('(617) 555-9999')
    expect(rebased.city).toBe('Somerville')
    expect(rebased.email).toBe('ana@example.com')
  })
})

describe('displayValue', () => {
  it('spells out lists, blanks, statuses, and dates', () => {
    const input = inputFromPatient({ ...patient, conditions: null, status: 'deceased' })
    expect(displayValue(input, 'allergies')).toBe('Penicillin, Latex')
    expect(displayValue(input, 'conditions')).toBe('Unknown')
    expect(displayValue(inputFromPatient(patient), 'conditions')).toBe('None known')
    expect(displayValue(input, 'email')).toBe('Blank')
    expect(displayValue(input, 'status')).toBe('Deceased')
    expect(displayValue(input, 'last_visit_date')).toBe('Sep 20, 2026')
  })
})
