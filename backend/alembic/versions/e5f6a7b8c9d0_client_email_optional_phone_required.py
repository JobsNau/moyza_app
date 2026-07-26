"""client_email_optional_phone_required

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-26 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # El correo pasa a ser opcional
    op.alter_column(
        'clients',
        'email',
        existing_type=sa.String(),
        nullable=True
    )

    # El teléfono pasa a ser obligatorio: los clientes existentes sin
    # teléfono se rellenan con cadena vacía para poder aplicar el NOT NULL
    op.execute("UPDATE clients SET phone = '' WHERE phone IS NULL")

    op.alter_column(
        'clients',
        'phone',
        existing_type=sa.String(),
        nullable=False
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.alter_column(
        'clients',
        'phone',
        existing_type=sa.String(),
        nullable=True
    )

    # Al volver atrás, el correo es obligatorio de nuevo
    op.execute("UPDATE clients SET email = '' WHERE email IS NULL")

    op.alter_column(
        'clients',
        'email',
        existing_type=sa.String(),
        nullable=False
    )
