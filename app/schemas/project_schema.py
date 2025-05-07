from datetime import date
from pydantic import BaseModel, EmailStr
from sqlalchemy import DateTime

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

class CheckInResponse(BaseModel):
    id: int
    project_id: int
    team_member_id: int
    checkin_date_usertz: date
    checkin_date_utctz: date
    did_yesterday: str
    doing_today: str
    blockers: str

#project_id={project_id}&user_email={user_email}&user_datetime={user_datetime}&user_checkinday={user_checkinday}&user_timezone={user_timezone}
class SubmitCheckInRequest(BaseModel):
    project_id: int
    did_yesterday: str
    doing_today: str
    blockers: str
    payload: str
