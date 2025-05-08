from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import func
from app.core.database import SessionLocal

from app.models.project_model import ProjectMemberModel
from app.models.response_model import CheckInResponseModel, CheckInResponseTracker
from app.schemas.checkin_response_schema import SubmitCheckInRequest
from app.schemas.response_schema import BaseResponse
from app.utils.security import decrypt_payload

from fastapi import status

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

    async def submit_checkin(self, request:SubmitCheckInRequest) -> BaseResponse[str]:
        try:

            payload = decrypt_payload(request.payload)
            with self.get_session() as db:
                team_member = db.query(ProjectMemberModel).filter(ProjectMemberModel.user_email == payload['user_email']).first()
                if not team_member:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="User with email not a team member of the project",
                        data=None
                    )
                
                checkin_tracker = db.query(CheckInResponseTracker).filter(CheckInResponseTracker.checkin_id == payload['checkin_id'],
                                                                          func.date(CheckInResponseTracker.user_checkin_date) == datetime.fromisoformat(payload['user_datetime']).date).first()
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
                
                submitted_response = db.query(CheckInResponseModel).filter(CheckInResponseModel.checkin_id == payload['checkin_id'],
                                                                            func.date(CheckInResponseModel.checkin_date_usertz) == datetime.fromisoformat(payload['user_datetime']).date,
                                                                            CheckInResponseModel.team_member_id == team_member.id).first()
                if submitted_response:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message=f"You have submitted the checkin for today - {payload['user_checkinday']}",
                        data=None
                    )

                response = CheckInResponseModel(
                    project_id = request.project_id,
                    team_member_id = team_member.id,
                    checkin_date_usertz = datetime.fromisoformat(payload['user_datetime']),
                    did_yesterday = request.did_yesterday,
                    doing_today = request.doing_today,
                    blocker = request.blockers,
                    checkin_day = payload['user_checkinday'],
                    date_created_utc = datetime.now(timezone.utc),
                    checkin_id = payload['checkin_id']
                )

                no_responses_recieved = checkin_tracker.number_of_responses_received + 1
                checkin_tracker.number_of_responses_received = no_responses_recieved

                if checkin_tracker.number_of_responses_expecting == checkin_tracker.number_of_responses_received:
                    #process analytics 
                    await self.process_analytics(payload['checkin_id'], datetime.fromisoformat(payload['user_datetime']))


                
                db.add(response)
                db.commit()

                return BaseResponse(
                        statusCode=status.HTTP_200_OK,
                        message="Response recorded successfully",
                        data=None
                    )

            
        except Exception as e:
            print(f'Error while recording response {e}')
            return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Error while trying to save your response",
                        data=None
                    )
        

    async def process_analytics(self, checkin_id:int, user_datetime:datetime):
        try:
            with self.get_session() as db:
                responses = db.query(CheckInResponseModel).filter(CheckInResponseModel.checkin_id == checkin_id, 
                                                                  CheckInResponseModel.checkin_date_usertz == user_datetime).all()
                
                #get project details
                #feed it into ai api 
                if len(responses) == 0:
                    return None
                
                #save result in db 
                #complete on the tracker 
        except Exception as e:
            return None