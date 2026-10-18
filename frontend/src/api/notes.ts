import { request } from './client'
import type { Note, NoteCreate, PatientSummary } from './types'

const base = (patientId: string) => `/patients/${encodeURIComponent(patientId)}`

/** Newest first. Deleted notes are left out. */
export function listNotes(patientId: string): Promise<Note[]> {
  return request(`${base(patientId)}/notes`)
}

export function createNote(patientId: string, note: NoteCreate): Promise<Note> {
  return request(`${base(patientId)}/notes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(note),
  })
}

/** A soft delete: the note is kept in the database, like marking it "entered in error". */
export function deleteNote(patientId: string, noteId: string): Promise<void> {
  return request(`${base(patientId)}/notes/${encodeURIComponent(noteId)}`, { method: 'DELETE' })
}

/**
 * The patient summary. When the server has a language model set up, the narrative is generated
 * from the full notes, and the first request for a new set of notes can take several seconds.
 * Otherwise, or if the model fails, the server returns its built-in narrative.
 */
export function getSummary(patientId: string): Promise<PatientSummary> {
  return request(`${base(patientId)}/summary`)
}
