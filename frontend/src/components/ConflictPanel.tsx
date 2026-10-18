import type { Patient } from '../api/types'
import {
  FIELD_LABELS,
  changedFields,
  displayValue,
  inputFromPatient,
  toPatientInput,
  type PatientField,
  type PatientFormValues,
} from '../pages/patientForm'

interface ConflictPanelProps {
  /** The version these edits started from. */
  base: Patient
  /** The version someone else saved in the meantime. */
  latest: Patient
  values: PatientFormValues
  /** The fields these edits change. */
  mine: PatientField[]
  onKeepMine: () => void
  onDiscardMine: () => void
}

/**
 * Shown when someone else saved the patient while this edit was open.
 *
 * Lists what they changed, and flags fields both people changed, since saving would replace
 * their value there. Nothing is saved from here: either choice puts their version in the form,
 * so staff look over the result before saving again.
 */
export function ConflictPanel({
  base,
  latest,
  values,
  mine,
  onKeepMine,
  onDiscardMine,
}: ConflictPanelProps) {
  const before = inputFromPatient(base)
  const theirs = inputFromPatient(latest)
  const yours = toPatientInput(values)
  const theirFields = changedFields(before, theirs)
  const overlap = theirFields.filter((field) => mine.includes(field))

  return (
    <section className="conflict" role="alert" aria-labelledby="conflict-heading">
      <h2 id="conflict-heading">Someone else changed this patient while you were editing</h2>
      {theirFields.length === 0 ? (
        <p>Their save didn't change any of the fields on this form.</p>
      ) : (
        <div className="table-wrap">
          <table className="data-table conflict-table">
            <thead>
              <tr>
                <th scope="col">Field</th>
                <th scope="col">When you started</th>
                <th scope="col">Their change</th>
                <th scope="col">Your change</th>
              </tr>
            </thead>
            <tbody>
              {theirFields.map((field) => {
                const both = overlap.includes(field)
                return (
                  <tr key={field} className={both ? 'conflict-both' : undefined}>
                    <th scope="row">
                      {FIELD_LABELS[field]}
                      {both && <span className="conflict-flag">You both changed this</span>}
                    </th>
                    <td>{displayValue(before, field)}</td>
                    <td>{displayValue(theirs, field)}</td>
                    <td>{both ? displayValue(yours, field) : <span className="muted">—</span>}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      <p>
        {overlap.length > 0
          ? 'If you keep your changes, yours replace theirs in the highlighted fields. '
          : ''}
        Either way, their other changes are kept and nothing is saved until you save again.
      </p>
      <div className="form-buttons">
        <button type="button" className="button button-primary" onClick={onKeepMine}>
          Keep my changes and review
        </button>
        <button type="button" className="button" onClick={onDiscardMine}>
          Discard my changes
        </button>
      </div>
    </section>
  )
}
