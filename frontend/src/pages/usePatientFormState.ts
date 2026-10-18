import { useState } from 'react'

import { ApiError } from '../api/client'
import { checkValues, type PatientField, type PatientFormValues } from './patientForm'

type Errors = Partial<Record<PatientField, string>>

/**
 * Form values plus the error messages to show, shared by the create and edit pages.
 *
 * The form's own checks appear after the first save attempt and update as staff type.
 * Messages from the API stay until that field is edited, since only a new save can re-check them.
 */
export function usePatientFormState(initial: () => PatientFormValues) {
  const [values, setValuesState] = useState(initial)
  const [attempted, setAttempted] = useState(false)
  const [serverErrors, setServerErrors] = useState<Errors>({})
  const [formError, setFormError] = useState<unknown>(null)

  const setValues = (next: PatientFormValues) => {
    const edited = (Object.keys(next) as PatientField[]).filter((f) => next[f] !== values[f])
    if (edited.some((field) => field in serverErrors)) {
      setServerErrors((current) => {
        const kept = { ...current }
        for (const field of edited) delete kept[field]
        return kept
      })
    }
    setValuesState(next)
  }

  const localErrors = checkValues(values)
  const errors: Errors = { ...serverErrors, ...(attempted ? localErrors : {}) }

  return {
    values,
    setValues,
    errors,
    /** A failure that isn't about one field, such as the server being unreachable. */
    formError,
    /** Call before saving. Returns false, and shows the problems, if the form isn't ready. */
    startSave() {
      setAttempted(true)
      setFormError(null)
      return Object.keys(localErrors).length === 0
    },
    /** Show a failed save: field problems next to the fields, anything else above the buttons. */
    showSaveError(error: unknown) {
      if (error instanceof ApiError && Object.keys(error.fieldErrors).length > 0) {
        setServerErrors(error.fieldErrors as Errors)
      } else {
        setFormError(error)
      }
    },
  }
}
