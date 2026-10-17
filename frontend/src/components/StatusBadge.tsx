import type { PatientStatus } from '../api/types'
import { STATUS_LABELS } from '../format'

export function StatusBadge({ status }: { status: PatientStatus }) {
  return <span className={`badge badge-${status}`}>{STATUS_LABELS[status]}</span>
}
