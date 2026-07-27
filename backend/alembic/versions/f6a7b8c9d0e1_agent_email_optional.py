"""agent_email_optional

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-26 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # El correo del agente pasa a ser opcional
    op.alter_column(
        'agents',
        'email',
        existing_type=sa.String(),
        nullable=True
    )


def downgrade() -> None:
    """Downgrade schema."""

    # Al volver atrás el correo es obligatorio de nuevo: se rellenan los
    # agentes sin correo con un valor único derivado del id
    op.execute(
        "UPDATE agents SET email = 'agente_' || id || '@sin-correo.local' "
        "WHERE email IS NULL"
    )

    op.alter_column(
        'agents',
        'email',
        existing_type=sa.String(),
        nullable=False
    )
