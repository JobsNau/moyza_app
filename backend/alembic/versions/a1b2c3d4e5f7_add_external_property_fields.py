"""add_external_property_fields

Revision ID: a1b2c3d4e5f7
Revises: f6a7b8c9d0e1
Create Date: 2026-07-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Columnas nuevas que replican la tabla externa de propiedades.
# `moneda` se trata aparte porque lleva valor por defecto y NOT NULL.
NEW_COLUMNS = (
    sa.Column('referencia', sa.String(), nullable=True),
    sa.Column('codigo', sa.String(), nullable=True),
    sa.Column('ref_catastral', sa.String(), nullable=True),
    sa.Column('estado_inmueble', sa.String(), nullable=True),
    sa.Column('situacion', sa.String(), nullable=True),
    sa.Column('pais', sa.String(), nullable=True),
    sa.Column('zona', sa.String(), nullable=True),
    sa.Column('cod_postal', sa.String(length=5), nullable=True),
    sa.Column('m2_utiles', sa.Numeric(10, 2), nullable=True),
    sa.Column('m2_construidos', sa.Numeric(10, 2), nullable=True),
    sa.Column('planta', sa.String(), nullable=True),
    sa.Column('num_dormitorios', sa.SmallInteger(), nullable=True),
    sa.Column('num_banos_aseos', sa.SmallInteger(), nullable=True),
    sa.Column('num_salones', sa.SmallInteger(), nullable=True),
    sa.Column('num_terrazas', sa.SmallInteger(), nullable=True),
    sa.Column('num_armarios', sa.SmallInteger(), nullable=True),
    sa.Column('num_garaje_aparcam', sa.SmallInteger(), nullable=True),
    sa.Column('num_ascensores', sa.SmallInteger(), nullable=True),
    sa.Column('num_despachos', sa.SmallInteger(), nullable=True),
    sa.Column('num_locales', sa.SmallInteger(), nullable=True),
    sa.Column('llaves', sa.Text(), nullable=True),
    sa.Column('mandato_acuerdo', sa.Text(), nullable=True),
    sa.Column('fecha_alta', sa.Date(), nullable=True),
)


def upgrade() -> None:
    """Upgrade schema."""

    for column in NEW_COLUMNS:
        op.add_column('properties', column)

    op.add_column(
        'properties',
        sa.Column(
            'moneda',
            sa.String(length=3),
            nullable=False,
            server_default='EUR'
        )
    )

    # Índice de apoyo para búsquedas por referencia.
    # No es único: todavía no se usa como clave de sincronización.
    op.create_index(
        'ix_properties_referencia',
        'properties',
        ['referencia']
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index('ix_properties_referencia', table_name='properties')

    op.drop_column('properties', 'moneda')

    for column in reversed(NEW_COLUMNS):
        op.drop_column('properties', column.name)
