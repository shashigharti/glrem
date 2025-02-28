from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from datetime import datetime, timezone
from .base import Base


class Earthquake(Base):
    __tablename__ = "earthquakes"

    id = Column(Integer, primary_key=True, index=True)
    eventid = Column(str, nullable=False, index=True)
    magnitude = Column(Float, nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
