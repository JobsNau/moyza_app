from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey

from sqlalchemy.orm import relationship

from app.db.base import Base


class PropertyAlert(Base):

    __tablename__ = "property_alerts"

    id = Column(Integer, primary_key=True, index=True)

    property_id = Column(
        Integer,
        ForeignKey("properties.id"),
        nullable=False
    )

    agent_id = Column(
        Integer,
        ForeignKey("agents.id"),
        nullable=False
    )

    # Información del interesado
    lead_name = Column(
        String,
        nullable=False
    )

    lead_phone = Column(
        String,
        nullable=True
    )

    lead_email = Column(
        String,
        nullable=True
    )

    source = Column(
        String,
        nullable=True
    )

    # Descripción de la alerta
    alert_type = Column(
        String,
        default="LEAD_INTERES"
    )

    message = Column(
        Text,
        nullable=True
    )

    priority = Column(
        String,
        default="NORMAL"
    )

    # Estado y seguimiento
    status = Column(
        String,
        default="PENDING"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    read_at = Column(
        DateTime,
        nullable=True
    )

    completed_at = Column(
        DateTime,
        nullable=True
    )

    # Auditoría
    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    buyer_id = Column(
        Integer,
        ForeignKey("buyers.id"),
        nullable=True
    )

    business_type = Column(
        String,
        nullable=True
    )

    # Relaciones
    property = relationship(
        "Property",
        backref="alerts"
    )

    agent = relationship(
        "Agent",
        backref="alerts"
    )

    buyer = relationship(
        "Buyer",
        back_populates="alerts"
    )

    follow_ups = relationship(
        "AlertFollowUp",
        back_populates="alert",
        cascade="all, delete-orphan"
    )
