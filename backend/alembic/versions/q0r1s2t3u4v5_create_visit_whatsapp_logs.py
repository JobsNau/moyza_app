"""create visit_whatsapp_logs

Revision ID: q0r1s2t3u4v5
Revises: p9q0r1s2t3u4
Create Date: 2026-09-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'q0r1s2t3u4v5'
down_revision = 'p9q0r1s2t3u4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'visit_whatsapp_logs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('visit_id', sa.Integer(), sa.ForeignKey('property_visits.id', ondelete='CASCADE'), nullable=False),
        sa.Column('property_id', sa.Integer(), sa.ForeignKey('properties.id', ondelete='SET NULL'), nullable=True),
        sa.Column('recipient_type', sa.String(), nullable=False),
        sa.Column('recipient_name', sa.String(), nullable=True),
        sa.Column('recipient_phone', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('trigger', sa.String(), nullable=False),
        sa.Column('file_url', sa.String(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('triggered_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('attempted_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_visit_whatsapp_logs_visit_id', 'visit_whatsapp_logs', ['visit_id'])
    op.create_index('ix_visit_whatsapp_logs_property_id', 'visit_whatsapp_logs', ['property_id'])
    op.create_index('ix_visit_whatsapp_logs_status', 'visit_whatsapp_logs', ['status'])
    op.create_index('ix_visit_whatsapp_logs_attempted_at', 'visit_whatsapp_logs', ['attempted_at'])


def downgrade():
    op.drop_index('ix_visit_whatsapp_logs_attempted_at', table_name='visit_whatsapp_logs')
    op.drop_index('ix_visit_whatsapp_logs_status', table_name='visit_whatsapp_logs')
    op.drop_index('ix_visit_whatsapp_logs_property_id', table_name='visit_whatsapp_logs')
    op.drop_index('ix_visit_whatsapp_logs_visit_id', table_name='visit_whatsapp_logs')
    op.drop_table('visit_whatsapp_logs')
