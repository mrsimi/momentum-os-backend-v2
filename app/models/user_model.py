from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from app.core.database import Base
from datetime import datetime, timezone

class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_guest = Column(Boolean, default=False)
    date_created = Column(DateTime, default=datetime.now(timezone.utc))
    date_updated = Column(DateTime, default=datetime.now(timezone.utc))
    last_login = Column(DateTime, default=datetime.now(timezone.utc))
    is_verified = Column(Boolean, default=False)
    to_changePassword = Column(Boolean, nullable=True)