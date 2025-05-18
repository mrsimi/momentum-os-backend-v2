from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from app.core.database import Base


class PlansModel(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    external_plan_id = Column(String, nullable=False)
    external_plan_name = Column(String, nullable=False)
    external_plan_code = Column(String, nullable=False)
    readable_name = Column(String, nullable=False)
    provider = Column(String, nullable=False)

class WebhookLogsModel(Base):
    __tablename__ = "webhooklogs"

    id = Column(Integer, primary_key=True)
    external_customer_id = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    event = Column(String, nullable=False)
    content = Column(String, nullable=False)
    date_created = Column(DateTime, default=datetime.now(timezone.utc))

class UserSubscriptionModel(Base):
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    stage = Column(String, nullable=False)
    external_customer_id = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    next_payment_date = Column(DateTime, nullable=True)
    date_created = Column(DateTime, default=datetime.now(timezone.utc))
    date_updated = Column(DateTime, default=datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    external_transaction_ref = Column(String, nullable=True)
    



