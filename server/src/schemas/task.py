from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TaskCreate(BaseModel):
    eventid: str
    location: str
    latitude: float
    longitude: float
    filename: str
    eventtype: str
    analysis: Optional[str] = None
    date: datetime
    status: Optional[str] = "Pending"


class TaskResponse(BaseModel):
    id: int
    eventid: str
    location: str
    latitude: float
    longitude: float
    filename: str
    eventtype: str
    analysis: Optional[str]
    date: datetime
    status: str

    class Config:
        from_attributes = True
