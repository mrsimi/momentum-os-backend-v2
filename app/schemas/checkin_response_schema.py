from datetime import date, datetime
from typing import List
from pydantic import BaseModel, EmailStr

class BaseCheckIn(BaseModel):
    did_yesterday: str
    doing_today: str
    blockers: str

class CheckInResponse(BaseCheckIn):
    id: int
    project_id: int
    team_member_id: int
    checkin_date_usertz: datetime

#project_id={project_id}&user_email={user_email}&user_datetime={user_datetime}&user_checkinday={user_checkinday}&user_timezone={user_timezone}
class SubmitCheckInRequest(BaseCheckIn):
    project_id: int
    payload: str

class CheckInAnalyticsRequest(BaseCheckIn):
    email: EmailStr
    team_member_id: int

class CheckInAnalyticsResponse(BaseModel):
    project_id: int
    checkin_date:date
    response_ids:List[int]
    summary:str
    blockers:str
    diversion_range: str
    diversion_context:str
    checkin_responses: List[CheckInAnalyticsRequest]

class GenerateSummaryRequest(BaseModel):
    project_id:int
    checkin_date:date
    force_generation:bool


