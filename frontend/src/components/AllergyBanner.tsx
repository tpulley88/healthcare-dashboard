/**
 * Allergies at the top of the chart, where staff look before ordering or giving anything.
 *
 * "Unknown" (null) is shown as a warning rather than calmly, because no record of allergies
 * isn't the same as no allergies.
 */
export function AllergyBanner({ allergies }: { allergies: string[] | null }) {
  if (allergies === null) {
    return (
      <div className="allergy-banner allergy-unknown">
        <strong>Allergies unknown</strong> — not yet recorded
      </div>
    )
  }
  if (allergies.length === 0) {
    return (
      <div className="allergy-banner allergy-none">
        <strong>No known allergies</strong>
      </div>
    )
  }
  return (
    <div className="allergy-banner allergy-present">
      <strong>Allergies:</strong> {allergies.join(', ')}
    </div>
  )
}
