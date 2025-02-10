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
    country: str
    eventdate: datetime
    startdate: datetime
    enddate: datetime
    areaofinterest: Optional[str] = ""
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
    country: str
    eventdate: datetime
    startdate: datetime
    enddate: datetime
    areaofinterest: Optional[str] = None
    status: str

    class Config:
        from_attributes = True
