from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class PropertyChangeLog(Base):
    __tablename__ = "property_change_logs"

    id = Column(Integer, primary_key=True, index=True)

    property_id = Column(
        Integer,
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    field_name = Column(String, nullable=False)
    field_label = Column(String, nullable=False)

    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)

    changed_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    changed_by = relationship("User")
