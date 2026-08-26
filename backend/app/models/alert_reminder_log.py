from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class AlertReminderLog(Base):
    __tablename__ = "alert_reminder_logs"

    id = Column(Integer, primary_key=True, index=True)

    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Guardamos nombre y email directamente para preservar el registro
    # aunque el agente sea eliminado posteriormente
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    agent_name = Column(String, nullable=False)
    agent_email = Column(String, nullable=False)

    buyers_count = Column(Integer, nullable=False, default=0)

    # SENT = email enviado, SKIPPED = omitido a propósito, ERROR = fallo técnico
    status = Column(String, nullable=False)

    skip_reason = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)

    agent = relationship("Agent")
