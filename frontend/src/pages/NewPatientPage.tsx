import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router'

import { createPatient } from '../api/patients'
import { ErrorMessage } from '../components/ErrorMessage'
import { PatientForm } from '../components/PatientForm'
import { emptyValues, toPatientInput } from './patientForm'
import { usePatientFormState } from './usePatientFormState'

export function NewPatientPage() {
  const form = usePatientFormState(emptyValues)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const mutation = useMutation({
    mutationFn: () => createPatient(toPatientInput(form.values)),
    onSuccess: async (patient) => {
      queryClient.setQueryData(['patient', patient.id], patient)
      await queryClient.invalidateQueries({ queryKey: ['patients'] })
      navigate(`/patients/${patient.id}`)
    },
    onError: form.showSaveError,
  })

  return (
    <section>
      <p className="back-link">
        <Link to="/patients">← All patients</Link>
      </p>
      <h1>New patient</h1>
      <PatientForm
        values={form.values}
        onChange={form.setValues}
        errors={form.errors}
        onSubmit={() => form.startSave() && mutation.mutate()}
        footer={
          <>
            {form.formError ? <ErrorMessage error={form.formError} /> : null}
            <div className="form-buttons">
              <button type="submit" className="button button-primary" disabled={mutation.isPending}>
                {mutation.isPending ? 'Saving…' : 'Create patient'}
              </button>
              <Link to="/patients" className="button">
                Cancel
              </Link>
            </div>
          </>
        }
      />
    </section>
  )
}
