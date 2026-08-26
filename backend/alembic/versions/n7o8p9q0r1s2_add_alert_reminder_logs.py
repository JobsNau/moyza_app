"""add alert reminder logs

Revision ID: n7o8p9q0r1s2
Revises: m6n7o8p9q0r1
Create Date: 2026-08-25

"""
from alembic import op
import sqlalchemy as sa

revision = 'n7o8p9q0r1s2'
down_revision = 'm6n7o8p9q0r1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'alert_reminder_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('executed_at', sa.DateTime(), nullable=False),
        sa.Column(
            'agent_id',
            sa.Integer(),
            sa.ForeignKey('agents.id', ondelete='SET NULL'),
            nullable=True
        ),
        sa.Column('agent_name', sa.String(), nullable=False),
        sa.Column('agent_email', sa.String(), nullable=False),
        sa.Column('buyers_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('skip_reason', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
    )
    op.create_index('ix_alert_reminder_logs_id', 'alert_reminder_logs', ['id'])
    op.create_index('ix_alert_reminder_logs_executed_at', 'alert_reminder_logs', ['executed_at'])


def downgrade():
    op.drop_index('ix_alert_reminder_logs_executed_at', table_name='alert_reminder_logs')
    op.drop_index('ix_alert_reminder_logs_id', table_name='alert_reminder_logs')
    op.drop_table('alert_reminder_logs')
