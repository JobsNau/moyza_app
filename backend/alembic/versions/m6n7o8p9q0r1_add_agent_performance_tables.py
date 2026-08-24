"""add agent performance tables

Revision ID: m6n7o8p9q0r1
Revises: l5m6n7o8p9q0
Create Date: 2026-08-21

"""
from alembic import op
import sqlalchemy as sa

revision = 'm6n7o8p9q0r1'
down_revision = 'l5m6n7o8p9q0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'agent_performance_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('period_type', sa.String(), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('contactos_venta', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('contactos_alquiler', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('bajadas', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('captaciones_crm', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('cierres', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('hojas_visita', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('calidad_cartera', sa.Float(), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('locked_at', sa.DateTime(), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('audio_file', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agent_performance_reports_id', 'agent_performance_reports', ['id'])
    op.create_index(
        'ix_agent_performance_reports_agent_period',
        'agent_performance_reports',
        ['agent_id', 'period_type', 'period_start'],
        unique=True,
    )

    op.create_table(
        'agent_performance_targets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('period_type', sa.String(), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('target_contactos', sa.Integer(), nullable=True),
        sa.Column('target_bajadas', sa.Integer(), nullable=True),
        sa.Column('target_captaciones_crm', sa.Integer(), nullable=True),
        sa.Column('target_cierres', sa.Integer(), nullable=True),
        sa.Column('target_hojas_visita', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agent_performance_targets_id', 'agent_performance_targets', ['id'])
    op.create_index(
        'ix_agent_performance_targets_agent_period',
        'agent_performance_targets',
        ['agent_id', 'period_type', 'period_start'],
        unique=True,
    )


def downgrade():
    op.drop_index('ix_agent_performance_targets_agent_period', 'agent_performance_targets')
    op.drop_index('ix_agent_performance_targets_id', 'agent_performance_targets')
    op.drop_table('agent_performance_targets')

    op.drop_index('ix_agent_performance_reports_agent_period', 'agent_performance_reports')
    op.drop_index('ix_agent_performance_reports_id', 'agent_performance_reports')
    op.drop_table('agent_performance_reports')
