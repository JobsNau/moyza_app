"""add user_activity_logs table

Revision ID: j3k4l5m6n7o8
Revises: i2j3k4l5m6n7
Create Date: 2026-08-18 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'j3k4l5m6n7o8'
down_revision = 'i2j3k4l5m6n7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_activity_logs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('method', sa.String(10), nullable=False),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
    )


def downgrade():
    op.drop_table('user_activity_logs')
