import type { FormEvent, ReactNode } from 'react'

import type { BloodType, PatientStatus } from '../api/types'
import { STATUS_LABELS } from '../format'
import {
  BLOOD_TYPES,
  FIELD_LABELS,
  US_STATES,
  type ListMode,
  type ListValue,
  type PatientField,
  type PatientFormValues,
  listEntries,
} from '../pages/patientForm'

type Errors = Partial<Record<PatientField, string>>

type TextField = Exclude<
  PatientField,
  'allergies' | 'conditions' | 'status' | 'blood_type' | 'state'
>

interface PatientFormProps {
  values: PatientFormValues
  onChange: (values: PatientFormValues) => void
  /** Messages shown under each field, from the form's own checks or from the API. */
  errors: Errors
  onSubmit: () => void
  /** Buttons and any message shown at the bottom of the form. */
  footer: ReactNode
}

/**
 * The fields for creating or editing a patient.
 * The parent owns the values and decides what saving means.
 */
export function PatientForm({ values, onChange, errors, onSubmit, footer }: PatientFormProps) {
  const set = <F extends keyof PatientFormValues>(field: F, value: PatientFormValues[F]) =>
    onChange({ ...values, [field]: value })

  const text = (field: TextField, props = {}) => (
    <Field field={field} error={errors[field]}>
      {(inputProps) => (
        <input
          {...inputProps}
          {...props}
          value={values[field]}
          onChange={(event) => set(field, event.target.value)}
        />
      )}
    </Field>
  )

  const submit = (event: FormEvent) => {
    event.preventDefault()
    onSubmit()
  }

  return (
    <form className="patient-form" onSubmit={submit} noValidate>
      <fieldset>
        <legend>Patient</legend>
        <div className="form-grid">
          {text('first_name', { required: true, maxLength: 100, autoComplete: 'off' })}
          {text('last_name', { required: true, maxLength: 100, autoComplete: 'off' })}
          {text('date_of_birth', { type: 'date', required: true })}
          <Field field="status" error={errors.status}>
            {(inputProps) => (
              <select
                {...inputProps}
                value={values.status}
                onChange={(event) => set('status', event.target.value as PatientStatus)}
              >
                {Object.entries(STATUS_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            )}
          </Field>
        </div>
      </fieldset>

      <fieldset>
        <legend>Clinical</legend>
        <ListField
          field="allergies"
          noneLabel="No known allergies"
          value={values.allergies}
          error={errors.allergies}
          onChange={(value) => set('allergies', value)}
        />
        <ListField
          field="conditions"
          noneLabel="No known conditions"
          value={values.conditions}
          error={errors.conditions}
          onChange={(value) => set('conditions', value)}
        />
        <div className="form-grid">
          <Field field="blood_type" error={errors.blood_type}>
            {(inputProps) => (
              <select
                {...inputProps}
                value={values.blood_type}
                onChange={(event) => set('blood_type', event.target.value as BloodType | '')}
              >
                <option value="">Not recorded</option>
                {BLOOD_TYPES.map((type) => (
                  <option key={type}>{type}</option>
                ))}
              </select>
            )}
          </Field>
          {text('last_visit_date', { type: 'date' })}
        </div>
      </fieldset>

      <fieldset>
        <legend>Contact</legend>
        {/* Laid out like a mailing address: street on its own line, then city, state, ZIP. */}
        <div className="contact-grid">
          {text('phone', { type: 'tel', placeholder: '(617) 555-0123' })}
          {text('email', { type: 'email', maxLength: 254 })}
          {text('street', { maxLength: 200 })}
          {text('city', { maxLength: 100 })}
          <Field field="state" error={errors.state}>
            {(inputProps) => (
              <select
                {...inputProps}
                value={values.state}
                onChange={(event) => set('state', event.target.value)}
              >
                {/* A short blank option, since the state column is narrow. */}
                <option value="">—</option>
                {US_STATES.map((code) => (
                  <option key={code}>{code}</option>
                ))}
              </select>
            )}
          </Field>
          {text('postal_code', { inputMode: 'numeric', placeholder: '02118', maxLength: 10 })}
        </div>
      </fieldset>

      <div className="form-footer">{footer}</div>
    </form>
  )
}

interface InputProps {
  id: string
  'aria-invalid': boolean
  'aria-describedby': string | undefined
}

/** A label, the control, and its error message, wired together for screen readers. */
function Field({
  field,
  error,
  children,
}: {
  field: PatientField
  error: string | undefined
  children: (props: InputProps) => ReactNode
}) {
  const id = `patient-${field}`
  return (
    <div className={`field field-${field}`}>
      <label htmlFor={id}>{FIELD_LABELS[field]}</label>
      {children({
        id,
        'aria-invalid': Boolean(error),
        'aria-describedby': error ? `${id}-error` : undefined,
      })}
      {error && (
        <span id={`${id}-error`} className="field-error">
          {error}
        </span>
      )}
    </div>
  )
}

/**
 * Allergies or conditions: unknown, none known, or a list.
 *
 * Unknown is the default for a new patient, so nobody records "none" without having asked.
 * Entries typed under "has" stay in place if another choice is picked,
 * so a mis-click doesn't lose them, but they are only saved while "has" is chosen.
 */
function ListField({
  field,
  noneLabel,
  value,
  error,
  onChange,
}: {
  field: 'allergies' | 'conditions'
  noneLabel: string
  value: ListValue
  error: string | undefined
  onChange: (value: ListValue) => void
}) {
  const label = FIELD_LABELS[field]
  const choices: [ListMode, string][] = [
    ['unknown', 'Unknown (not yet asked)'],
    ['none', noneLabel],
    ['has', `Has ${label.toLowerCase()}`],
  ]
  const id = `patient-${field}`
  const hiddenCount = value.mode === 'has' ? 0 : listEntries(value.text).length

  return (
    <fieldset
      className="list-field"
      aria-invalid={Boolean(error)}
      aria-describedby={error ? `${id}-error` : undefined}
    >
      <legend>{label}</legend>
      <div className="choices">
        {choices.map(([mode, text]) => (
          <label key={mode} className="choice">
            <input
              type="radio"
              name={field}
              value={mode}
              checked={value.mode === mode}
              onChange={() => onChange({ ...value, mode })}
            />
            {text}
          </label>
        ))}
      </div>
      {value.mode === 'has' && (
        <div className="field">
          <label htmlFor={id}>One per line</label>
          <textarea
            id={id}
            rows={3}
            value={value.text}
            aria-invalid={Boolean(error)}
            onChange={(event) => onChange({ ...value, text: event.target.value })}
          />
        </div>
      )}
      {hiddenCount > 0 && (
        <p className="muted small">
          {hiddenCount === 1 ? '1 entry' : `${hiddenCount} entries`} will be removed when you save.
          Choose "Has {label.toLowerCase()}" to keep {hiddenCount === 1 ? 'it' : 'them'}.
        </p>
      )}
      {error && (
        <span id={`${id}-error`} className="field-error">
          {error}
        </span>
      )}
    </fieldset>
  )
}
