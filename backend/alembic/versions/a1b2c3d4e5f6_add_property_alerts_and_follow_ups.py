"""add property alerts and follow ups tables

Revision ID: a1b2c3d4e5f6
Revises: f432dcf50003
Create Date: 2026-07-07 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f432dcf50003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create property_alerts table
    op.create_table(
        'property_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('lead_name', sa.String(), nullable=False),
        sa.Column('lead_phone', sa.String(), nullable=True),
        sa.Column('lead_email', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('alert_type', sa.String(), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('priority', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_property_alerts_id'), 'property_alerts', ['id'], unique=False)

    # Create alert_follow_ups table
    op.create_table(
        'alert_follow_ups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('next_action_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['alert_id'], ['property_alerts.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_follow_ups_id'), 'alert_follow_ups', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_alert_follow_ups_id'), table_name='alert_follow_ups')
    op.drop_table('alert_follow_ups')
    op.drop_index(op.f('ix_property_alerts_id'), table_name='property_alerts')
    op.drop_table('property_alerts')
