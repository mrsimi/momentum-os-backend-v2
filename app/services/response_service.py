from contextlib import contextmanager
from datetime import date, datetime, time, timedelta, timezone
import logging
import os
import socket

from sqlalchemy import any_, func, literal, text
from sqlalchemy.orm import joinedload
from fastapi import status

from app.core.database import SessionLocal
from app.infra.email_infra import EmailInfra
from app.models.project_model import CheckinModel, ProjectMemberModel, ProjectModel
from app.models.response_model import CheckInResponseModel, CheckInResponseTracker, CheckInResponsesInsights
from app.schemas.checkin_response_schema import CheckInAnalyticsRequest, CheckInAnalyticsResponse, GenerateSummaryRequest, SendCheckInReminderRequest, SubmitCheckInRequest
from app.schemas.response_schema import BaseResponse
from app.services.ai_service import AiService
from app.utils.security import decrypt_payload, encrypt_payload

logging.basicConfig(
    format="%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
    level=logging.INFO
)

FRONTEND_URL = os.getenv('FRONTEND_URL')

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
    
    def is_blocker_present(self, text: str) -> bool:
        if not text or not text.strip():
            return False
        normalized = text.strip().lower()
        return normalized not in ['none', 'no blockers', 'n/a', 'na', 'nope', ''] and len(normalized) > 3

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
                    checkin_id=payload['checkin_id'],
                    has_blocker = self.is_blocker_present(request.blockers)
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
                return BaseResponse(
                    statusCode=status.HTTP_400_BAD_REQUEST,
                    message="No responses found for this day",
                    data=None
                )

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
            logging.info(f'Error while generating ai response {e}')
            return BaseResponse(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="Error while generating ai summary",
                data=None
            )

    def get_check_analytics(self, project_id:int, checkin_date:date) -> BaseResponse[CheckInAnalyticsResponse]:
        try:
            if checkin_date > datetime.now().date():
                return BaseResponse(
                                statusCode=status.HTTP_400_BAD_REQUEST,
                                message="No checks yet, you've selected a future date",
                                data=None
                            )
            with self.get_session() as db:
                analytics = db.query(CheckInResponsesInsights).filter(CheckInResponsesInsights.project_id == project_id,
                                                                      func.date(CheckInResponsesInsights.checkin_date) == checkin_date).first()
                if not analytics:
                    checkin = db.query(CheckinModel).filter(CheckinModel.project_id == project_id).first()
                    if not checkin:
                        return BaseResponse(
                            statusCode=status.HTTP_400_BAD_REQUEST,
                            message="No checkin set for this project. Kindly contact customer care with the title of the project",
                            data=None
                        )
                    
                    checkin_tracker = db.query(CheckInResponseTracker).filter(CheckInResponseTracker.checkin_id == checkin.id,
                                                                              func.date(CheckInResponseTracker.user_checkin_date) == checkin_date).first()
                    
                    current_day = checkin_date.strftime("%A")
                    #current_time = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=int(checkin.user_timezone))))
                    
                    if current_day in checkin.user_checkin_days:
                        if not checkin_tracker:
                            return BaseResponse(
                                statusCode=status.HTTP_400_BAD_REQUEST,
                                message="Checks have not been sent in yet",
                                data=None
                            )
                        
                        if checkin_tracker.number_of_responses_received == 0:
                            return BaseResponse(
                                statusCode=status.HTTP_400_BAD_REQUEST,
                                message="No checkins submitted yet",
                                data=None
                            )
                        if checkin_tracker.number_of_responses_expecting != checkin_tracker.number_of_responses_received:
                            return BaseResponse(
                                statusCode=status.HTTP_417_EXPECTATION_FAILED,
                                message=f"Expecting {checkin_tracker.number_of_responses_expecting}, but {checkin_tracker.number_of_responses_received} response(s) have been submitted. Do you want to still generate insights?",
                                data=None
                            )
                        
                        if checkin_tracker.number_of_responses_expecting == checkin_tracker.number_of_responses_received:
                            return BaseResponse(
                                statusCode=status.HTTP_417_EXPECTATION_FAILED,
                                message=f"Insights not generated, kindly use the Generate insights button",
                                data=None
                            )
                    else:
                        return BaseResponse(
                            statusCode=status.HTTP_400_BAD_REQUEST,
                            message="There are no checks setup for today",
                            data=None
                        )
                
                else:
                    responses = db.query(CheckInResponseModel) \
                        .options(joinedload(CheckInResponseModel.team_member)) \
                        .filter(
                            CheckInResponseModel.id.in_(analytics.response_ids)
                        ).all()
                    
                    members_responses = [
                        CheckInAnalyticsRequest(
                            did_yesterday=res.did_yesterday,
                            doing_today=res.doing_today,
                            blockers=res.blocker,
                            email=res.team_member.user_email,
                            team_member_id=res.team_member_id
                        ) for res in responses
                    ]

                    analytics_res = CheckInAnalyticsResponse(
                        project_id=project_id, 
                        checkin_date=checkin_date,
                        response_ids=analytics.response_ids,
                        summary=analytics.summary,
                        blockers=analytics.blockers, 
                        diversion_context=analytics.diversion_context,
                        diversion_range=analytics.diversion_range,
                        checkin_responses=members_responses
                    )

                    return BaseResponse(
                        statusCode=status.HTTP_200_OK,
                        message="Success",
                        data=analytics_res
                    )


        except Exception as e:
            logging.info(f'Error while getting response {e}')
            return BaseResponse(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="Error while trying to get response",
                data=None
            )

    def generate_checkin_summary(self, request: GenerateSummaryRequest) -> BaseResponse[str]:
        try:
            if request.checkin_date > datetime.now().date():
                return BaseResponse(
                                statusCode=status.HTTP_400_BAD_REQUEST,
                                message="No checks yet, you've selected a future date",
                                data=None
                            )
            with self.get_session() as db:
                analytics = db.query(CheckInResponsesInsights).filter(CheckInResponsesInsights.project_id == request.project_id,
                                                                      func.date(CheckInResponsesInsights.checkin_date) == request.checkin_date).first()
                if analytics:
                    return BaseResponse(
                            statusCode=status.HTTP_400_BAD_REQUEST,
                            message="Summary already generated for this project",
                            data=None
                        )
                
                checkin = db.query(CheckinModel).filter(CheckinModel.project_id == request.project_id).first()
                if not checkin:
                    return BaseResponse(
                            statusCode=status.HTTP_400_BAD_REQUEST,
                            message="No checkin set for this project. Kindly contact customer care with the title of the project",
                            data=None
                        )
                checkin_response_tracker = db.query(CheckInResponseTracker)\
                    .filter(CheckInResponseTracker.checkin_id == checkin.id, 
                            func.date(CheckInResponseTracker.user_checkin_date) == request.checkin_date).first()
                
                if not checkin_response_tracker:
                    return BaseResponse(
                            statusCode=status.HTTP_400_BAD_REQUEST,
                            message="No checkins sent for this day",
                            data=None
                        )
                else:
                    if checkin_response_tracker.number_of_responses_received == 0:
                        return BaseResponse(
                            statusCode=status.HTTP_400_BAD_REQUEST,
                            message="No checkins submitted yet",
                            data=None
                        )

                    if checkin_response_tracker.number_of_responses_expecting != \
                        checkin_response_tracker.number_of_responses_received and \
                            request.force_generation == False:
                        return BaseResponse(
                                    statusCode=status.HTTP_417_EXPECTATION_FAILED,
                                    message=f"Expecting {checkin_response_tracker.number_of_responses_expecting}, but {checkin_response_tracker.number_of_responses_received} response(s) have been submitted. Do you want to continue",
                                    data=None
                                )
                    
                    if checkin_response_tracker.number_of_responses_expecting == \
                        checkin_response_tracker.number_of_responses_received or \
                        request.force_generation == True:

                        analytics_res = self.process_analytics(
                            checkin.id,
                            datetime.combine(request.checkin_date, time.min),
                            request.project_id,
                            checkin_response_tracker.id,
                            db
                        )
                        if analytics_res.statusCode != status.HTTP_200_OK:
                            return analytics_res
                        
                        checkin_response_tracker.status = "COMPLETED_AI_PROCESS"
                        checkin_response_tracker.is_analytics_processed = True

                        db.commit()

                        return BaseResponse(
                            statusCode=status.HTTP_200_OK,
                            message="Insights generated successfully",
                            data=None
                        )


        except Exception as e:
            logging.info(f'Error while getting response {e}')
            return BaseResponse(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="Error while trying to get response",
                data=None
            )
        
    def get_trends(self, user_id:int):

        try:
            with self.get_session() as db:
                fourteen_days_ago = datetime.now() - timedelta(days=14)

                query = text("""
                    SELECT 
                        cr.checkin_date_usertz::date AS checkin_date,
                        COUNT(*) AS total_checkins,
                        COUNT(*) FILTER (WHERE cr.has_blocker = TRUE) AS total_blockers
                    FROM checkin_responses cr
                    JOIN projects p ON cr.project_id = p.id
                    WHERE p.creator_user_id = :user_id
                    AND p.date_created > :date_created
                    GROUP BY checkin_date
                    ORDER BY checkin_date
                """)

                result = db.execute(query, {
                    "user_id": user_id,
                    "date_created": fourteen_days_ago.date().isoformat()
                })

                rows = result.fetchall()

                # Optional: print rows for debugging
                for row in rows:
                    print(row)

                data = [
                    {
                        "date": row[0].strftime("%Y-%m-%d"),
                        "updates": row[1],
                        "blockers": row[2] or 0,
                    }
                    for row in rows
                ]

                return BaseResponse(
                    statusCode=status.HTTP_200_OK,
                    message="Success",
                    data=data
                )

                
                
        except Exception as e:
            logging.info(f'Error while getting response {e}')
            return BaseResponse(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="Error while trying to get response",
                data=None
            )
        
    def send_reminder(self, request: SendCheckInReminderRequest) -> BaseResponse[str]:

        try:
            #get_day
            user_checkinday = request.checkin_date.strftime("%A")
            email_infra = EmailInfra()
            with self.get_session() as db:
                project = db.query(ProjectModel).filter(ProjectModel.creator_user_id == request.creator_user_id, 
                                                        ProjectModel.id == request.project_id,
                                                        ProjectModel.is_active == True).first()
                
                if not project:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Project not found",
                        data=None
                    )
                
                checkin_date: date = request.checkin_date
                start_date: date = project.start_date.date() if isinstance(project.start_date, datetime) else project.start_date
                end_date: date = project.end_date.date() if isinstance(project.end_date, datetime) else project.end_date

                if checkin_date < start_date or checkin_date > end_date:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Invalid date selected for this project",
                        data=None
                    )
                

                checkin =db.query(CheckinModel).filter(
                        CheckinModel.project_id == request.project_id,
                        CheckinModel.is_active == True,
                        user_checkinday == any_(CheckinModel.user_checkin_days)
                    ).first()

                if not checkin:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Invalid checkin for this project",
                        data=None
                    )
                
                checkin_tracker = db.query(CheckInResponseTracker).filter(
                                        CheckInResponseTracker.checkin_id == checkin.id, 
                                        func.date(CheckInResponseTracker.user_checkin_date) == request.checkin_date
                                    ).first()
                
                if not checkin_tracker:
                    #create tracker and send
                    team_members = db.query(ProjectMemberModel).filter(ProjectMemberModel.project_id == request.project_id,
                                                                        ProjectMemberModel.is_active == True).all()
                    for member in team_members:
                        if member.user_email.lower().strip() == request.member_email.lower().strip():
                            user_email = member.user_email
                            payload = {
                                    "user_email": user_email,
                                    "user_datetime":request.checkin_date.isoformat(),
                                    "user_checkinday": user_checkinday,
                                    "user_timezone": checkin.user_timezone,
                                    "checkin_id": checkin.id
                            }
                            logging.info(payload)
                            encrypted_payload = encrypt_payload(payload)
                            link = f"{FRONTEND_URL}/check-in?project_id={request.project_id}&payload={encrypted_payload}"

                            logging.info(f'-- found member and link: {link}')
                            email_infra.send_email(user_email, "Submit Your CheckIn", "submit_checkin", {"link": link})
                    
                    checkin_tracker = CheckInResponseTracker(
                        status = 'EMAILS_SENT',
                        number_of_responses_expecting = len(team_members),
                        user_checkin_date = request.checkin_date,
                        checkin_id = checkin.id,
                        date_created = datetime.now(timezone.utc), 
                        from_server_name = socket.gethostname()
                    )
                    db.add(checkin_tracker)
                    db.commit()

                    return BaseResponse(
                        statusCode=status.HTTP_200_OK,
                        message="Emails sent successfully",
                        data=None
                    )

                else:
                    if checkin_tracker.is_analytics_processed:
                        return BaseResponse(
                            statusCode=status.HTTP_400_BAD_REQUEST,
                            message="Analytics has been generated for this day cannot submit checkin anymore",
                            data=None
                        )
                    else:
                        #send emails to team members
                        team_members = db.query(ProjectMemberModel).filter(ProjectMemberModel.project_id == request.project_id,
                                                                        ProjectMemberModel.is_active == True).all()
                        
                        for member in team_members:
                            if member.user_email.lower().strip() == request.member_email.lower().strip():
                                user_email = member.user_email
                                payload = {
                                        "user_email": user_email,
                                        "user_datetime": checkin_tracker.user_checkin_date.isoformat(),
                                        "user_checkinday": user_checkinday,
                                        "user_timezone": checkin.user_timezone,
                                        "checkin_id": checkin_tracker.id
                                }
                                logging.info(payload)
                                encrypted_payload = encrypt_payload(payload)
                                link = f"{FRONTEND_URL}/check-in?project_id={request.project_id}&payload={encrypted_payload}"

                                logging.info(f'-- found member and link: {link}')
                                email_infra.send_email(user_email, "Submit Your CheckIn", "submit_checkin", {"link": link})
                                
                                return BaseResponse(
                                    statusCode=status.HTTP_200_OK,
                                    message="Emails sent successfully",
                                    data=None
                                )
                            
                            else:
                                return BaseResponse(
                                    statusCode=status.HTTP_400_BAD_REQUEST,
                                    message="Invalid Email",
                                    data=None
                                )



        except Exception as e:
            logging.info(f'Error while trying to send reminder {e}')
            return BaseResponse(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="Error while trying to send reminder",
                data=None
            )
