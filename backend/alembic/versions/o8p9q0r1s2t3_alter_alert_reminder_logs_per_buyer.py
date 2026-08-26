"""alter alert_reminder_logs: one row per buyer/alert

Revision ID: o8p9q0r1s2t3
Revises: n7o8p9q0r1s2
Create Date: 2026-08-25

"""
from alembic import op
import sqlalchemy as sa

revision = 'o8p9q0r1s2t3'
down_revision = 'n7o8p9q0r1s2'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('alert_reminder_logs', 'buyers_count')

    op.add_column(
        'alert_reminder_logs',
        sa.Column(
            'alert_id',
            sa.Integer(),
            sa.ForeignKey('property_alerts.id', ondelete='SET NULL'),
            nullable=True
        )
    )
    op.add_column(
        'alert_reminder_logs',
        sa.Column('buyer_name', sa.String(), nullable=True)
    )


def downgrade():
    op.drop_column('alert_reminder_logs', 'buyer_name')
    op.drop_column('alert_reminder_logs', 'alert_id')

    op.add_column(
        'alert_reminder_logs',
        sa.Column('buyers_count', sa.Integer(), nullable=False, server_default='0')
    )
