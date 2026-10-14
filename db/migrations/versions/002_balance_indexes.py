from alembic import op

revision = "002"
down_revision = "001"


def upgrade():
    op.execute("CREATE INDEX payment_invoice ON finance.payment(org_id,invoice_id)")
    op.execute("CREATE INDEX credit_invoice ON finance.credit_note(org_id,invoice_id)")


def downgrade():
    op.execute("DROP INDEX finance.payment_invoice")
    op.execute("DROP INDEX finance.credit_invoice")
