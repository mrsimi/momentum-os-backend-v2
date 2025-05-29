from contextlib import contextmanager
from datetime import date, datetime, timezone
import logging

from sqlalchemy import extract, func

from app.core.database import SessionLocal
from app.models.project_model import ProjectModel
from fastapi import status
from app.models.response_model import CheckInResponsesInsights, GeneratedContent
from app.schemas.response_schema import BaseResponse
from app.services.ai_service import AiService
from app.services.subscription_service import SubscriptionService
from sqlalchemy.dialects.postgresql import ARRAY, BIGINT
from sqlalchemy import cast


logging.basicConfig(
    format="%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
    level=logging.INFO
)

class ContentGenerationService:
    def __init__(self):
        self.db = SessionLocal()
        self.ai = AiService()

    def __del__(self):
        self.db.close()

    @contextmanager
    def get_session(self):
        try:
            yield self.db
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        finally:
            self.db.close()
    
    def generate_content(self, check_dates:list[date], project_id:int, user_id:int):
        """
        Generate content based on check-in dates, project ID, and user ID.
        This is a placeholder for the actual content generation logic.
        """
        logging.info(f"Generating content for project {project_id} and user {user_id} on dates: {check_dates}")

        with self.get_session() as session:
            # Here you would typically query the database or perform operations
            # For example, fetching project details or user information
            project = session.query(ProjectModel).filter(ProjectModel.id == project_id, 
                                                            ProjectModel.creator_user_id == user_id).first()
            if not project:
                return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="User not the creator of the project",
                        data=None
                    )
            
            responses = session.query(CheckInResponsesInsights).filter(
                CheckInResponsesInsights.project_id == project_id,
                func.date(CheckInResponsesInsights.checkin_date).in_(check_dates)
            ).all()

            if len(responses) == 0:
                return BaseResponse(
                    statusCode=status.HTTP_404_NOT_FOUND,
                    message="No responses found for the given dates.",
                    data=None
                )
            
            summaries = [r.summary for r in responses if len(r.summary) > 0]

            if len(summaries) == 0:
                return BaseResponse(
                    statusCode=status.HTTP_400_BAD_REQUEST,
                    message="No responses found for the given dates.",
                    data=None
                )
            
            if len(summaries) == 1:
                # If only one summary, return it directly
                 return BaseResponse(
                    statusCode=status.HTTP_400_BAD_REQUEST,
                    message="One response found which is not enough to generate content.",
                    data=None
                )
            
            response_ids = [r.id for r in responses]


            previous_content = session.query(GeneratedContent).filter(
                GeneratedContent.project_id == project_id,
                GeneratedContent.checkin_response_ids.contains(
                    cast(response_ids, ARRAY(BIGINT))
                )
            ).first()

            if previous_content:
                return BaseResponse(
                    statusCode=status.HTTP_200_OK,
                    message="Content already generated for the given dates.",
                    data={"content_id": previous_content.id, "content": previous_content.content}
                )

            if not responses:
                return BaseResponse(
                    statusCode=status.HTTP_404_NOT_FOUND,
                    message="No responses found for the given dates.",
                    data=None
                )
            
            get_plan = SubscriptionService().get_user_subscription(user_id, session)

            now = datetime.now(timezone.utc)
            current_year = now.year
            current_month = now.month

            content_count = session.query(GeneratedContent).filter(
                GeneratedContent.user_id == user_id,
                extract('year', GeneratedContent.date_created) == current_year,
                extract('month', GeneratedContent.date_created) == current_month
            ).count()

            plan_limits = {
                0: 3,   # free plan limit
                1: 10,  # basic plan limit
            }

            plan_id = get_plan.data.plan_id
            limit = plan_limits.get(plan_id)

            if limit is not None and content_count >= limit:
                return BaseResponse(
                    statusCode=status.HTTP_403_FORBIDDEN,
                    message="You have reached your content generation limit for this month.",
                    data=None
                )
            
            content = self.ai.generate_content(
                summaries=[response.summary for response in responses],
                description=project.description
            )

            

            saved_content = GeneratedContent(
                content=content,
                checkin_id=project.id,
                project_id=project_id,
                checkin_dates=check_dates,
                checkin_response_ids=[response.id for response in responses],
                date_created=func.now(),
                content_type="behind-the-scene",  # Example content type
                user_id=user_id
            )

            session.add(saved_content)
            session.commit()

            return BaseResponse(
                statusCode=status.HTTP_200_OK,
                message="Content generated successfully.",
                data={"content_id": saved_content.id, "content": content}
            )
        # Implement the actual content generation logic here
        return {"status": "success", "message": "Content generated successfully."}
