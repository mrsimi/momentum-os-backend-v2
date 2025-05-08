

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from app.core.database import Base


class CheckInResponseModel(Base):
    __tablename__ = "checkin_responses"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, index=True)
    team_member_id = Column(Integer, index=True)
    checkin_date_usertz = Column(DateTime) 
    checkin_date_utctz = Column(DateTime)
    did_yesterday = Column(String)
    doing_today = Column(String)
    blocker = Column(String)
    checkin_day = Column(String)
    checkin_id = Column(Integer, index=True)
    date_created_utc = Column(DateTime)

class CheckInResponseTracker(Base):
    __tablename__ = "checkin_response_tracker"

    id = Column(Integer, primary_key=True)
    status = Column(String)
    number_of_responses_expecting = Column(Integer)
    number_of_responses_received = Column(Integer)
    is_analytics_processed = Column(Boolean)
    user_checkin_date = Column(DateTime)
    checkin_id = Column(Integer)
    date_created=Column(DateTime)


