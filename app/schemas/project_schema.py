from datetime import date
from pydantic import BaseModel, EmailStr

class ProjectRequest(BaseModel):
    title: str
    description: str
    start_date: date
    end_date: date
    checkin_time: str #24 hour
    checkin_days: list[str]
    members_emails: list[EmailStr]
    timezone: str

class ProjectResponse(BaseModel):
    id: int
    title: str
    description: str
    start_date: date
    end_date: date
    state: str

class ProjectDetailsResponse(BaseModel):
    id: int
    title: str
    description: str
    start_date: date
    end_date: date
    state: str
    checkin_time: str #24 hour
    checkin_days: list[str]
    members_emails: list[EmailStr]
    timezone: str