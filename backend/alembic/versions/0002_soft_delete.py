"""soft delete patients and notes

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-16

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FK_NAME = "fk_notes_patient_id_patients"
TABLES = ("patients", "notes")


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # Postgres can't alter a foreign key's ON DELETE action in place, so recreate it.
    op.drop_constraint(FK_NAME, "notes", type_="foreignkey")
    op.create_foreign_key(FK_NAME, "notes", "patients", ["patient_id"], ["id"], ondelete="RESTRICT")

    # Reject physical deletes from every client, not only the API.
    # A database superuser can still get around it (by disabling triggers or using TRUNCATE),
    # so it protects against mistakes, not against deliberate tampering.
    op.execute("""
        CREATE FUNCTION prevent_hard_delete() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '% rows are soft-deleted; set deleted_at instead', TG_TABLE_NAME
                USING ERRCODE = 'restrict_violation';
        END
        $$
    """)
    for table in TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_prevent_hard_delete BEFORE DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION prevent_hard_delete()"
        )


# Warning: this drops the deleted_at columns,
# so deleted patients and notes reappear as live records.
def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP TRIGGER {table}_prevent_hard_delete ON {table}")
    op.execute("DROP FUNCTION prevent_hard_delete()")

    op.drop_constraint(FK_NAME, "notes", type_="foreignkey")
    op.create_foreign_key(FK_NAME, "notes", "patients", ["patient_id"], ["id"], ondelete="CASCADE")

    for table in TABLES:
        op.drop_column(table, "deleted_at")
