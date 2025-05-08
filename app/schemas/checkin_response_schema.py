from datetime import date
from pydantic import BaseModel


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
