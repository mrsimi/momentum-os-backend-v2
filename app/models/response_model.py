

from datetime import datetime, timezone
from sqlalchemy import  Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY

from app.core.database import Base
from sqlalchemy.orm import relationship

class CheckInResponseModel(Base):
    __tablename__ = "checkin_responses"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, index=True)
    team_member_id = Column(Integer, ForeignKey("project_members.id"), index=True) 
    checkin_date_usertz = Column(DateTime) 
    checkin_date_utctz = Column(DateTime)
    did_yesterday = Column(String)
    doing_today = Column(String)
    blocker = Column(String)
    checkin_day = Column(String)
    checkin_id = Column(Integer, index=True)
    date_created_utc = Column(DateTime)
    has_blocker=Column(Boolean)

    team_member = relationship(
                        "ProjectMemberModel", 
                        backref="checkin_responses", 
                        primaryjoin="CheckInResponseModel.team_member_id == ProjectMemberModel.id",
                        lazy="joined")
    


class CheckInResponseTracker(Base):
    __tablename__ = "checkin_response_tracker"

    id = Column(Integer, primary_key=True)
    status = Column(String)
    number_of_responses_expecting = Column(Integer)
    number_of_responses_received = Column(Integer, default=0)
    is_analytics_processed = Column(Boolean, default=False)
    user_checkin_date = Column(DateTime)
    checkin_id = Column(Integer)
    date_created=Column(DateTime)
    from_server_name = Column(String, nullable=True)

class CheckInAnalyticsModel(Base):
    __tablename__ = "checkin_analytics"

    id = Column(Integer, primary_key=True)
    summary=Column(String)
    user_checkin_date=Column(DateTime)
    project_id = Column(Integer)
    checkin_id = Column(Integer, index=True)
    checkin_responseIds = Column(ARRAY(Integer))
    date_created=Column(DateTime)
    blockers_summary=Column(String)
    responses_corr_with_project_description=Column(String)
    diversion=Column(String)

class CheckInResponsesInsights(Base):
    __tablename__ = "checkin_responses_insights"

    id = Column(Integer, primary_key=True)
    tracker_id = Column(Integer, primary_key=True, nullable=False)
    checkin_id = Column(Integer, nullable=False, index=True)
    project_id = Column(Integer, nullable=False, index=True)
    checkin_date = Column(DateTime, nullable=False)
    response_ids = Column(ARRAY(Integer), nullable=False)
    summary = Column(String, nullable=True)
    blockers = Column(String, nullable=True)
    diversion_range = Column(String, nullable=True)
    diversion_context = Column(String, nullable=True)
    date_created = Column(DateTime, default=datetime.now(timezone.utc))

class GeneratedContent(Base):
    __tablename__ = "generated_contents"

    id = Column(Integer, primary_key=True)
    content = Column(String, nullable=False)
    checkin_id = Column(Integer, nullable=False, index=True)
    project_id = Column(Integer, nullable=False, index=True)
    date_created = Column(DateTime, default=datetime.now(timezone.utc))
    checkin_dates = Column(ARRAY(DateTime), nullable=False)
    checkin_response_ids = Column(ARRAY(Integer), nullable=True)  # IDs of check-in responses related to this content
    content_type = Column(String, nullable=False)  # e.g., "blog", "pitch", etc.
    user_id = Column(Integer, nullable=False, index=True)  # ID of the user who generated this content
    





