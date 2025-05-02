from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Time
from app.core.database import Base


class ProjectModel(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True)
    description = Column(String)
    creator_user_id = Column(Integer, index=True)
    date_created = Column(DateTime, default=datetime.now(timezone.utc))
    date_updated = Column(DateTime, default=datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    has_ended = Column(Boolean, default=False)

class CheckinModel(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, index=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    user_checkin_time = Column(Time)
    user_checkin_days = Column(String)
    user_timezone = Column(String)
    checkin_time_utc = Column(Time)
    is_active = Column(Boolean, default=True)
    date_created = Column(DateTime, default=datetime.now(timezone.utc))
    date_updated = Column(DateTime, default=datetime.now(timezone.utc))
    last_run_time_utc = Column(Time, nullable=True)
    project_ended = Column(Boolean, default=False)
    checkin_days_utc = Column(String)


class ProjectMemberModel(Base):
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True, nullable=True)
    date_created = Column(DateTime, default=datetime.now(timezone.utc))
    date_updated = Column(DateTime, default=datetime.now(timezone.utc))
    is_active = Column(Boolean, default=False)
    is_creator = Column(Boolean, default=False)
    is_guest = Column(Boolean, default=False)
    is_member = Column(Boolean, default=False)
    user_email = Column(String, nullable=True)
    has_accepted = Column(Boolean, default=False)
    has_rejected = Column(Boolean, default=False)
