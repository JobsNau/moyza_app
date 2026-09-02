from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class VisitWhatsappLog(Base):
    """Auditoría de cada intento de envío de la ficha de visita por WhatsApp."""

    __tablename__ = "visit_whatsapp_logs"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    visit_id = Column(
        Integer,
        ForeignKey("property_visits.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    property_id = Column(
        Integer,
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # A quién iba dirigido el envío
    recipient_type = Column(String, nullable=False)  # 'comprador' | 'agente'
    recipient_name = Column(String, nullable=True)
    recipient_phone = Column(String, nullable=True)

    # SENT = enviado con éxito, ERROR = falló el envío, SKIPPED = no se intentó (sin teléfono)
    status = Column(String, nullable=False, index=True)
    error_message = Column(Text, nullable=True)

    # Origen del intento: 'finalize' (automático al firmar) | 'manual_resend' (botón Enviar)
    trigger = Column(String, nullable=False)

    file_url = Column(String, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    triggered_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    attempted_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    visit = relationship("PropertyVisit", back_populates="whatsapp_logs")
    property = relationship("Property")
    triggered_by_user = relationship("User")
