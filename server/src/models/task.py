from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    eventid = Column(Integer, index=True)
    location = Column(String, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    filename = Column(String, index=True)
    eventtype = Column(String, index=True)
    analysis = Column(String)
    country = Column(String)
    eventdate = Column(DateTime, default=datetime.utcnow)
    status = Column(String, index=True)
    startdate = Column(DateTime, default=datetime.utcnow)
    enddate = Column(DateTime, default=datetime.utcnow)
    areaofinterest = Column(String)

    userid = Column(Integer, ForeignKey("users.id"), index=True)
    user = relationship("User", back_populates="tasks")
