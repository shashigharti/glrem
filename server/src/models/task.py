from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .base import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    eventid = Column(Integer, index=True, nullable=False)
    eventtype = Column(String, index=True, nullable=False)
    eventdate = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    location = Column(String, index=True, nullable=False)
    country = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    magnitude = Column(Float, nullable=False)

    startdate = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    enddate = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    filename = Column(String)
    analysis = Column(String)
    areaofinterest = Column(String)
    status = Column(String, nullable=False)
    asset = Column(String)

    userid = Column(String, ForeignKey("users.userid"), index=True, nullable=False)
    user = relationship("User", back_populates="tasks")
