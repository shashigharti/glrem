from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from datetime import datetime, timezone
from .base import Base


class Flood(Base):
    __tablename__ = "floods"

    id = Column(Integer, primary_key=True)
    water_level = Column(String, nullable=False)
    location = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
