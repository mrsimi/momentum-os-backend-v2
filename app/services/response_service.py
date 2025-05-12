from contextlib import contextmanager
from datetime import date, datetime, timezone
import logging

from sqlalchemy import func
from sqlalchemy.orm import joinedload
from fastapi import status

from app.core.database import SessionLocal
from app.models.project_model import CheckinModel, ProjectMemberModel, ProjectModel
from app.models.response_model import CheckInResponseModel, CheckInResponseTracker, CheckInResponsesInsights
from app.schemas.checkin_response_schema import CheckInAnalyticsRequest, CheckInAnalyticsResponse, SubmitCheckInRequest
from app.schemas.response_schema import BaseResponse
from app.services.ai_service import AiService
from app.utils.security import decrypt_payload

logging.basicConfig(
    format="%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
    level=logging.INFO
)

class ResponseService:
    def __init__(self):
        self.db = SessionLocal()

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

    def submit_checkin(self, request: SubmitCheckInRequest) -> BaseResponse[str]:
        try:
            payload = decrypt_payload(request.payload)
            with self.get_session() as db:
                team_member = db.query(ProjectMemberModel).filter(
                    ProjectMemberModel.user_email == payload['user_email']
                ).first()

                if not team_member:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="User with email not a team member of the project",
                        data=None
                    )

                checkin_tracker = db.query(CheckInResponseTracker).filter(
                    CheckInResponseTracker.checkin_id == payload['checkin_id'],
                    func.date(CheckInResponseTracker.user_checkin_date) == datetime.fromisoformat(payload['user_datetime']).date()
                ).first()

                if not checkin_tracker:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Trying to submit invalid response",
                        data=None
                    )

                if checkin_tracker.number_of_responses_expecting == checkin_tracker.number_of_responses_received:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message=f"All Updates have been submitted for {payload['user_checkinday']}",
                        data=None
                    )

                submitted_response = db.query(CheckInResponseModel).filter(
                    CheckInResponseModel.checkin_id == payload['checkin_id'],
                    func.date(CheckInResponseModel.checkin_date_usertz) == datetime.fromisoformat(payload['user_datetime']).date(),
                    CheckInResponseModel.team_member_id == team_member.id
                ).first()

                if submitted_response:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message=f"You have submitted the checkin for today - {payload['user_checkinday']}",
                        data=None
                    )

                response = CheckInResponseModel(
                    project_id=request.project_id,
                    team_member_id=team_member.id,
                    checkin_date_usertz=datetime.fromisoformat(payload['user_datetime']),
                    did_yesterday=request.did_yesterday,
                    doing_today=request.doing_today,
                    blocker=request.blockers,
                    checkin_day=payload['user_checkinday'],
                    date_created_utc=datetime.now(timezone.utc),
                    checkin_id=payload['checkin_id']
                )

                checkin_tracker.number_of_responses_received += 1

                db.add(response)
                db.commit()

                if checkin_tracker.number_of_responses_expecting == checkin_tracker.number_of_responses_received:
                    
                    checkin_tracker.status ="ABOUT_TO_AI_PROCESS"
                    analytics_res = self.process_analytics(
                        payload['checkin_id'],
                        datetime.fromisoformat(payload['user_datetime']),
                        request.project_id,
                        checkin_tracker.id,
                        db
                    )
                    if analytics_res.statusCode != status.HTTP_200_OK:
                        return analytics_res
                    
                    checkin_tracker.status = "COMPLETED_AI_PROCESS"
                    checkin_tracker.is_analytics_processed = True

                #db.add(response)
                db.commit()

                return BaseResponse(
                    statusCode=status.HTTP_200_OK,
                    message="Response recorded successfully",
                    data=None
                )

        except Exception as e:
            logging.info(f'Error while recording response {e}')
            return BaseResponse(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="Error while trying to save your response",
                data=None
            )

    def process_analytics(self, checkin_id: int, user_datetime: datetime,
                          project_id: int, tracker_id: int, db):
        try:
            responses = db.query(CheckInResponseModel) \
                .options(joinedload(CheckInResponseModel.team_member)) \
                .filter(
                    CheckInResponseModel.checkin_id == checkin_id,
                    CheckInResponseModel.project_id == project_id,
                    func.date(
                        CheckInResponseModel.checkin_date_usertz) == user_datetime.date()
                ).all()

            if len(responses) == 0:
                return None

            members_responses = [
                CheckInAnalyticsRequest(
                    did_yesterday=res.did_yesterday,
                    doing_today=res.doing_today,
                    blockers=res.blocker,
                    email=res.team_member.user_email,
                    team_member_id=res.team_member_id
                ) for res in responses
            ]

            product_doc = db.query(ProjectModel).filter(
                ProjectModel.id == project_id).first().description

            ai = AiService()
            ai_response = ai.process_response(members_responses, product_doc)

            insight = CheckInResponsesInsights(
                tracker_id=tracker_id,
                checkin_id=checkin_id,
                project_id=project_id,
                checkin_date=user_datetime,
                response_ids=[res.id for res in responses],
                summary=ai_response['summary'],
                blockers=ai_response['blockers'],
                diversion_range=ai_response['diversion_range'],
                diversion_context=ai_response['diversion_context'],
            )

            db.add(insight)
            db.commit()
            return BaseResponse(
                statusCode=status.HTTP_200_OK,
                message="Response recorded successfully",
                data=None
            )

        except Exception as e:
            logging.info(f'Error while recording response {e}')
            return BaseResponse(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="Error while trying to save your response",
                data=None
            )

    # def get_check_analytics(self, project_id:int, checkin_date:date) -> BaseResponse[CheckInAnalyticsResponse]:
    #     try:
    #         with self.get_session() as db:
    #             analytics = db.query(CheckInResponsesInsights).filter(CheckInResponsesInsights.project_id == project_id,
    #                                                                   func.date(CheckInResponsesInsights.checkin_date) == checkin_date)
    #             if not analytics:
    #                 checkin = db.query(CheckinModel).first(CheckinModel.project_id == project_id)
    #                 if not checkin:
    #                     return BaseResponse(
    #                         statusCode=status.HTTP_400_BAD_REQUEST,
    #                         message="No checkin set for this project. Kindly contact customer care with the title of the project",
    #                         data=None
    #                     )
                    
    #                 current_day = checkin_date.strftime("%A")
    #                 if current_day in checkin.user_checkin_days:
    #                     return BaseResponse(
    #                         statusCode=status.HTTP_400_BAD_REQUEST,
    #                         message="No checkin set for this project. Kindly contact customer care with the title of the project",
    #                         data=None
    #                     )

    #     except Exception e:
