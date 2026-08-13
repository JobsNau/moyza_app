"""add buyer_search_criteria table

Revision ID: i2j3k4l5m6n7
Revises: h1i2j3k4l5m6
Create Date: 2026-08-13 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'i2j3k4l5m6n7'
down_revision = 'h1i2j3k4l5m6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'buyer_search_criteria',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('buyer_id', sa.Integer(), sa.ForeignKey('buyers.id'), nullable=False),
        sa.Column('agent_id', sa.Integer(), sa.ForeignKey('agents.id'), nullable=True),
        sa.Column('zones', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('cities', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('property_type', sa.String(), nullable=True),
        sa.Column('business_type', sa.String(), nullable=True),
        sa.Column('min_price', sa.Numeric(), nullable=True),
        sa.Column('max_price', sa.Numeric(), nullable=True),
        sa.Column('min_bedrooms', sa.SmallInteger(), nullable=True),
        sa.Column('max_bedrooms', sa.SmallInteger(), nullable=True),
        sa.Column('min_bathrooms', sa.SmallInteger(), nullable=True),
        sa.Column('min_m2', sa.Numeric(), nullable=True),
        sa.Column('max_m2', sa.Numeric(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('buyer_id'),
    )
    op.create_index(op.f('ix_buyer_search_criteria_id'), 'buyer_search_criteria', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_buyer_search_criteria_id'), table_name='buyer_search_criteria')
    op.drop_table('buyer_search_criteria')
