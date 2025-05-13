from datetime import date
from pydantic import BaseModel, EmailStr

from app.schemas.checkin_response_schema import CheckInResponse

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
    members: list['ProjectMemberResponse'] 
    timezone: str
    checkin_responses: list['CheckInResponse'] 
    should_have_checkin: bool

class ProjectMemberResponse(BaseModel):
    id: int
    user_email: EmailStr
    is_creator: bool
    has_accepted: bool
    has_rejected: bool
    is_guest: bool
    is_active: bool

class ProjectAnalyticsResponse(BaseModel):
    active_projects:int
    team_members:int
    submitted_responses:int 
    active_projects_last_month:int

class ProjectDashboardResponse(BaseModel):
    analytics: ProjectAnalyticsResponse
    projects: list[ProjectResponse]
