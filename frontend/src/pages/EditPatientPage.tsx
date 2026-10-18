import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

import { ApiError } from '../api/client'
import { getPatient, updatePatient } from '../api/patients'
import type { Patient } from '../api/types'
import { ConflictPanel } from '../components/ConflictPanel'
import { ErrorMessage } from '../components/ErrorMessage'
import { PatientForm } from '../components/PatientForm'
import { fullName } from '../format'
import {
  changedFields,
  inputFromPatient,
  pickFields,
  rebaseValues,
  toPatientInput,
  valuesFromPatient,
} from './patientForm'
import { usePatientFormState } from './usePatientFormState'

export function EditPatientPage() {
  const { patientId = '' } = useParams()
  const { data, error, isPending, refetch } = useQuery({
    queryKey: ['patient', patientId],
    queryFn: () => getPatient(patientId),
  })

  return (
    <section>
      <p className="back-link">
        <Link to={`/patients/${patientId}`}>← Back to chart</Link>
      </p>
      {data ? (
        <>
          {/* A failed background refresh mustn't unmount the form and lose unsaved edits. */}
          {error && <ErrorMessage error={error} onRetry={() => refetch()} />}
          {/* The form copies the patient once, so a background refetch can't overwrite typing. */}
          <EditForm key={data.id} loaded={data} />
        </>
      ) : isPending ? (
        <p className="muted">Loading patient…</p>
      ) : (
        <ErrorMessage error={error} onRetry={() => refetch()} />
      )}
    </section>
  )
}

function EditForm({ loaded }: { loaded: Patient }) {
  // The saved version these edits started from. It changes only when staff accept a newer one.
  const [base, setBase] = useState(loaded)
  // Set when someone else saved first: their version, waiting for staff to decide.
  const [latest, setLatest] = useState<Patient | null>(null)
  const form = usePatientFormState(() => valuesFromPatient(loaded))
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const input = toPatientInput(form.values)
  const mine = changedFields(inputFromPatient(base), input)

  const mutation = useMutation({
    mutationFn: () => updatePatient(base.id, pickFields(input, mine), base.version),
    onSuccess: async (patient) => {
      queryClient.setQueryData(['patient', patient.id], patient)
      // The summary repeats profile fields, and the list shows several of them.
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['patient', patient.id, 'summary'] }),
        queryClient.invalidateQueries({ queryKey: ['patients'] }),
      ])
      navigate(`/patients/${patient.id}`)
    },
    onError: async (error) => {
      if (!(error instanceof ApiError && error.status === 412)) {
        form.showSaveError(error)
        return
      }
      try {
        const current = await getPatient(base.id)
        queryClient.setQueryData(['patient', current.id], current)
        setLatest(current)
      } catch (loadError) {
        form.showSaveError(loadError)
      }
    },
  })

  const resolve = (keepMine: boolean) => {
    if (!latest) return
    form.setValues(keepMine ? rebaseValues(latest, form.values, mine) : valuesFromPatient(latest))
    setBase(latest)
    setLatest(null)
    mutation.reset()
  }

  const save = () => {
    if (form.startSave() && mine.length > 0) mutation.mutate()
  }

  return (
    <>
      <h1>Edit {fullName(base)}</h1>
      {latest && (
        <ConflictPanel
          base={base}
          latest={latest}
          values={form.values}
          mine={mine}
          onKeepMine={() => resolve(true)}
          onDiscardMine={() => resolve(false)}
        />
      )}
      <PatientForm
        values={form.values}
        onChange={form.setValues}
        errors={form.errors}
        onSubmit={save}
        footer={
          <>
            {form.formError ? <ErrorMessage error={form.formError} /> : null}
            <div className="form-buttons">
              <button
                type="submit"
                className="button button-primary"
                disabled={mutation.isPending || mine.length === 0 || latest !== null}
              >
                {mutation.isPending ? 'Saving…' : 'Save changes'}
              </button>
              <Link to={`/patients/${base.id}`} className="button">
                Cancel
              </Link>
              {mine.length === 0 && <span className="muted small">No changes yet</span>}
            </div>
          </>
        }
      />
    </>
  )
}
