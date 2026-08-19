"""add business_type to property_alerts

Revision ID: l5m6n7o8p9q0
Revises: k4l5m6n7o8p9
Create Date: 2026-08-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'l5m6n7o8p9q0'
down_revision = 'k4l5m6n7o8p9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'property_alerts',
        sa.Column('business_type', sa.String(), nullable=True)
    )


def downgrade():
    op.drop_column('property_alerts', 'business_type')
