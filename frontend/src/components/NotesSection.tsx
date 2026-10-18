import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { ApiError } from '../api/client'
import { createNote, deleteNote, listNotes } from '../api/notes'
import type { Note } from '../api/types'
import { formatDateTime, localDateTimeNow, withLocalOffset } from '../format'
import { ErrorMessage } from './ErrorMessage'

const MAX_NOTE_LENGTH = 10_000

/** The full notes, newest first, as they'd appear in a chart, with adding and deleting. */
export function NotesSection({ patientId }: { patientId: string }) {
  const { data, error, isPending, refetch } = useQuery({
    queryKey: ['patient', patientId, 'notes'],
    queryFn: () => listNotes(patientId),
  })

  return (
    <section className="card" aria-labelledby="notes-heading">
      <h2 id="notes-heading">Notes{data ? ` (${data.length})` : ''}</h2>
      <NoteForm patientId={patientId} />
      {isPending ? (
        <p className="muted">Loading notes…</p>
      ) : !data ? (
        <ErrorMessage error={error} onRetry={() => refetch()} />
      ) : (
        <>
          {/* A failed background refresh keeps the notes being read on screen. */}
          {error && <ErrorMessage error={error} onRetry={() => refetch()} />}
          {data.length === 0 ? (
            <p className="muted">No notes yet.</p>
          ) : (
            <ol className="note-list">
              {data.map((note) => (
                <NoteItem key={note.id} note={note} />
              ))}
            </ol>
          )}
        </>
      )}
    </section>
  )
}

/** Adding or deleting a note changes both the notes list and the summary. */
function useRefreshNotes(patientId: string) {
  const queryClient = useQueryClient()
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['patient', patientId, 'notes'] }),
      queryClient.invalidateQueries({ queryKey: ['patient', patientId, 'summary'] }),
    ])
}

function NoteForm({ patientId }: { patientId: string }) {
  const [takenAt, setTakenAt] = useState(localDateTimeNow)
  const [content, setContent] = useState('')
  const refresh = useRefreshNotes(patientId)

  const mutation = useMutation({
    mutationFn: () => createNote(patientId, { taken_at: withLocalOffset(takenAt), content }),
    onSuccess: async () => {
      setContent('')
      setTakenAt(localDateTimeNow())
      await refresh()
    },
  })

  const fieldErrors = mutation.error instanceof ApiError ? mutation.error.fieldErrors : {}
  // Field problems show next to the field; anything else shows above the form.
  const formError = mutation.error && Object.keys(fieldErrors).length === 0 ? mutation.error : null

  const submit = (event: FormEvent) => {
    event.preventDefault()
    mutation.mutate()
  }

  return (
    <form className="note-form" onSubmit={submit} noValidate>
      {formError && <ErrorMessage error={formError} />}
      <label className="field">
        <span>Date and time of care</span>
        <input
          type="datetime-local"
          required
          value={takenAt}
          aria-invalid={Boolean(fieldErrors.taken_at)}
          aria-describedby={fieldErrors.taken_at ? 'taken-at-error' : undefined}
          onChange={(event) => setTakenAt(event.target.value)}
        />
        {fieldErrors.taken_at && (
          <span id="taken-at-error" className="field-error">
            {fieldErrors.taken_at}
          </span>
        )}
      </label>
      <label className="field">
        <span>Note</span>
        <textarea
          rows={4}
          required
          maxLength={MAX_NOTE_LENGTH}
          value={content}
          aria-invalid={Boolean(fieldErrors.content)}
          aria-describedby={fieldErrors.content ? 'content-error' : undefined}
          onChange={(event) => setContent(event.target.value)}
        />
        {fieldErrors.content && (
          <span id="content-error" className="field-error">
            {fieldErrors.content}
          </span>
        )}
      </label>
      <div>
        <button
          type="submit"
          className="button button-primary"
          disabled={mutation.isPending || !takenAt || !content.trim()}
        >
          {mutation.isPending ? 'Saving…' : 'Add note'}
        </button>
      </div>
    </form>
  )
}

function NoteItem({ note }: { note: Note }) {
  const [confirming, setConfirming] = useState(false)
  const refresh = useRefreshNotes(note.patient_id)
  const mutation = useMutation({
    mutationFn: () => deleteNote(note.patient_id, note.id),
    onSuccess: refresh,
  })

  return (
    <li className="note">
      <div className="note-header">
        <time dateTime={note.taken_at}>{formatDateTime(note.taken_at)}</time>
        {!confirming && (
          <button type="button" className="link-button" onClick={() => setConfirming(true)}>
            Delete
          </button>
        )}
      </div>
      <p className="note-content">{note.content}</p>
      {confirming && (
        <div className="confirm" role="group" aria-label="Confirm deleting this note">
          <span>Mark this note as entered in error? It will be removed from the chart.</span>
          <button
            type="button"
            className="button button-danger"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? 'Deleting…' : 'Delete note'}
          </button>
          <button
            type="button"
            className="button"
            disabled={mutation.isPending}
            onClick={() => {
              setConfirming(false)
              mutation.reset()
            }}
          >
            Cancel
          </button>
        </div>
      )}
      {mutation.error && <ErrorMessage error={mutation.error} />}
    </li>
  )
}
