"""add purchase_fees to property visits

Revision ID: p9q0r1s2t3u4
Revises: o8p9q0r1s2t3
Create Date: 2026-09-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'p9q0r1s2t3u4'
down_revision = 'o8p9q0r1s2t3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('property_visits', sa.Column('purchase_fees', sa.String(), nullable=True))


def downgrade():
    op.drop_column('property_visits', 'purchase_fees')
