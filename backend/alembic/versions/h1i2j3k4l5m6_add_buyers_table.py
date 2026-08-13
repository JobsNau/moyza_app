"""add buyers table and buyer_id to property_alerts

Revision ID: h1i2j3k4l5m6
Revises: g5h6i7j8k9l0
Create Date: 2026-08-13 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'h1i2j3k4l5m6'
down_revision = 'a1b2c3d4e5f7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'buyers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_buyers_id'), 'buyers', ['id'], unique=False)

    op.add_column(
        'property_alerts',
        sa.Column('buyer_id', sa.Integer(), sa.ForeignKey('buyers.id'), nullable=True)
    )


def downgrade():
    op.drop_column('property_alerts', 'buyer_id')
    op.drop_index(op.f('ix_buyers_id'), table_name='buyers')
    op.drop_table('buyers')
