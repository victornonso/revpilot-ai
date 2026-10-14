"""Tenant-isolated commercial facts, operations, governance and analytical views."""

from pathlib import Path

from alembic import op

revision = "001"
down_revision = None


def upgrade():
    op.execute(
        Path(__file__).resolve().parents[2].joinpath("sql/schema.sql").read_text()
    )


def downgrade():
    raise RuntimeError(
        "Destructive platform downgrade requires an explicit data migration."
    )
