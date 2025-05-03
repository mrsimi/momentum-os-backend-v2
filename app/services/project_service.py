from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import os
from app.core.database import SessionLocal
from app.infra.email_infra import EmailInfra
from app.models.project_model import CheckInResponseModel, CheckinModel, ProjectMemberModel, ProjectModel
from app.models.user_model import UserModel
from app.schemas.project_schema import CheckInResponse, ProjectDetailsResponse, ProjectMemberResponse, ProjectRequest, ProjectResponse
from app.schemas.response_schema import BaseResponse
from app.utils.helpers import convert_time_utc_with_tz, convert_utc_days_and_time
from psycopg2 import errors
from sqlalchemy.exc import IntegrityError

from fastapi import status

from app.utils.security import decrypt_payload, encrypt_payload

class ProjectService:
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

    def create_project(self, project_request:ProjectRequest, user_id:int) -> BaseResponse[str]:
        
        #verify they can create project or not based on subscription. 
        try:
            checkin_days_utc, checkin_time_utc = convert_utc_days_and_time(project_request.checkin_days,
                                                        project_request.checkin_time,
                                                        project_request.timezone)
            #members 

            with self.get_session() as db:
                #check if user already exists
                user = db.query(UserModel).filter(UserModel.id == user_id).first()
                if not user:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="User not found",
                        data=None
                    )

                #get members with their email 
                members_already_user = db.query(UserModel).filter(UserModel.email.in_(project_request.members_emails)).all()
                members_not_users = [email for email in project_request.members_emails if email not in [member.email for member in members_already_user]]

                project = ProjectModel(
                    title=project_request.title,
                    description=project_request.description,
                    creator_user_id=user_id,
                    start_date=project_request.start_date,
                    end_date=project_request.end_date,
                )
                db.add(project)
                db.commit()

                checkin = CheckinModel(
                    project_id=project.id,
                    user_checkin_time=project_request.checkin_time,
                    user_checkin_days=project_request.checkin_days,
                    user_timezone=project_request.timezone,
                    checkin_time_utc=checkin_time_utc,
                    checkin_days_utc = checkin_days_utc
                )

                db.add(checkin)


                list_of_members = []
                list_of_members.extend(ProjectMemberModel(
                    project_id=project.id,
                    user_id=member.id,
                    is_active=False,
                    is_creator=False,
                    is_guest=False,
                    is_member=True,
                    user_email=member.email
                ) for member in members_already_user)

                list_of_members.extend(ProjectMemberModel(
                    project_id=project.id,
                    user_id=None,
                    is_active=False,
                    is_creator=False,
                    is_guest=True,
                    is_member=False,
                    user_email=email
                ) for email in members_not_users)

                list_of_members.append(ProjectMemberModel(
                    project_id=project.id,
                    user_id=user_id,
                    is_active=True,
                    is_creator=True,
                    is_guest=False,
                    is_member=True,
                    user_email=user.email,
                    has_accepted=True
                ))

                db.add_all(list_of_members)
                db.commit()

                #send email to all members who are not users.
                self.send_emails_to_members(project_request.members_emails
                                            , project.title, project.id, user.email)

                return BaseResponse(
                    statusCode=status.HTTP_200_OK,
                    message="Project created successfully",
                    data=project.id
                )
        except IntegrityError as e:
            db.rollback()
            if 'projects_title_key' in str(e.orig):
                return BaseResponse(
                    statusCode=status.HTTP_400_BAD_REQUEST,
                    message="Project title already exists",
                    data=None
                )
            else:
                return BaseResponse(
                    statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message="Internal server error",
                    data=None
                )

        except Exception as e:
            print(f"Error creating project: {e}")
            return BaseResponse(
                statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Internal server error",
                data=None
            )

        
    def get_projects_by_creator_id(self, user_id:int) -> BaseResponse[list[ProjectResponse]]:
        with self.get_session() as db:
            projects = db.query(ProjectModel).filter(ProjectModel.creator_user_id == user_id).all()
            if not projects:
                return BaseResponse(
                    statusCode=status.HTTP_400_BAD_REQUEST,
                    message="Project not found",
                    data=None
                )
            
            projects_response = [
                ProjectResponse(
                    id=project.id,
                    title=project.title,
                    description=project.description,
                    start_date=project.start_date,
                    end_date=project.end_date,
                    state= self.get_project_status(project)
                ) for project in projects
            ]
            return BaseResponse(
                statusCode=status.HTTP_200_OK,
                message="Project found",
                data= projects_response
            )
    
    def get_project_status(self, project: ProjectModel):
        return (
            'active' if project.is_active and not project.has_ended else
            'ended' if project.has_ended else
            'expired' if project.end_date.date() < date.today() else
            'deactivated'
        )
    
    def deactivate_project(self, project_id:int, user_id:int) -> BaseResponse[str]:
        with self.get_session() as db:
            project = db.query(ProjectModel).filter(ProjectModel.id == project_id and ProjectModel.creator_user_id == user_id).first()
            if not project:
                return BaseResponse(
                    statusCode=status.HTTP_400_BAD_REQUEST,
                    message="Project not found",
                    data=None
                )
            project.is_active = False

            checkin = db.query(CheckinModel).filter(CheckinModel.project_id == project_id).first()
            if checkin:
                checkin.is_active = False
                checkin.date_updated = datetime.now(timezone.utc)
                
            db.commit()
            return BaseResponse(
                statusCode=status.HTTP_200_OK,
                message="Project deactivated successfully",
                data=project_id
            )
    
    def complete_project(self, project_id:int, user_id:int) -> BaseResponse[str]:
        with self.get_session() as db:
            project = db.query(ProjectModel).filter(ProjectModel.id == project_id and ProjectModel.creator_user_id == user_id).first()
            if not project:
                return BaseResponse(
                    statusCode=status.HTTP_400_BAD_REQUEST,
                    message="Project not found",
                    data=None
                )
            project.is_active = False
            project.has_ended = True
            project.date_updated = datetime.now(timezone.utc)

            checkin = db.query(CheckinModel).filter(CheckinModel.project_id == project_id).first()
            if checkin:
                checkin.is_active = False
                checkin.date_updated = datetime.now(timezone.utc)
                
            db.commit()
            return BaseResponse(
                statusCode=status.HTTP_200_OK,
                message="Project completed successfully",
                data=project_id
            )
    
    def send_emails_to_members(self, emails:list[str], project_title:str, project_id:int, creator_email:str):
        #send emails to all members who are not users.
        email_infra = EmailInfra()

        for email in emails:
            accept_encrypted_payload_url = encrypt_payload({"project_id": project_id, "email": email, "action": "accept"})
            reject_encrypted_payload_url = encrypt_payload({"project_id": project_id, "email": email, "action": "reject"})
            

            # send email verification
            email_infra.send_email(
                destinationEmail=email,
                subject="Join a Project",
                type="join_team",
                object={
                    "accept_link": f"{os.getenv('FRONTEND_URL')}/click?upnpa={accept_encrypted_payload_url}",
                    "reject_link": f"{os.getenv('FRONTEND_URL')}/click?upnpa={reject_encrypted_payload_url}",
                    "project_name": project_title,
                    "creator_email": creator_email
                }
            )
            #send email to the user
            
    def submit_project_invite_response(self, encrypted_payload:str) -> BaseResponse[str]:
        #decrypt the payload and get the project id and email
        decrypted_payload = decrypt_payload(encrypted_payload)
        project_id = decrypted_payload.get("project_id")
        email = decrypted_payload.get("email")
        action = decrypted_payload.get("action")
        #check if the action is accept or reject
        if action == "accept":
            return self.accept_project(project_id, email)
        elif action == "reject":
            return self.reject_project(project_id, email)
        else:
            return BaseResponse(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="Invalid action",
                data=None
            )
        
    def accept_project(self, project_id:int, email:str) -> BaseResponse[str]:
        with self.get_session() as db:
            #check if the project exists and the user exists
            project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
            if not project:
                return BaseResponse(
                    statusCode=status.HTTP_400_BAD_REQUEST,
                    message="Project not found",
                    data=None
                )
            project_member = db.query(ProjectMemberModel).filter(ProjectMemberModel.user_email == email).first()
            if not project_member:
                return BaseResponse(
                    statusCode=status.HTTP_400_BAD_REQUEST,
                    message="User not found",
                    data=None
                )
            
            project_member.is_active = True
            project_member.has_accepted = True
            project_member.date_updated = datetime.now(timezone.utc)
            db.commit()
            return BaseResponse(
                statusCode=status.HTTP_200_OK,
                message="Project accepted successfully",
                data=project_id
            )

    def reject_project(self, project_id:int, email:str) -> BaseResponse[str]:
        with self.get_session() as db:
            #check if the project exists and the user exists
            project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
            if not project:
                return BaseResponse(
                    statusCode=status.HTTP_400_BAD_REQUEST,
                    message="Project not found",
                    data=None
                )
            project_member = db.query(ProjectMemberModel).filter(ProjectMemberModel.user_email == email).first()
            if not project_member:
                return BaseResponse(
                    statusCode=status.HTTP_400_BAD_REQUEST,
                    message="User not found",
                    data=None
                )
            
            project_member.is_active = False
            project_member.has_accepted = False
            project_member.has_rejected = True
            project_member.date_updated = datetime.now(timezone.utc)
            db.commit()
            return BaseResponse(
                statusCode=status.HTTP_200_OK,
                message="Project rejected successfully",
                data=project_id
            )
        
    def get_project_details(self, project_id:int, creator_user_id:int) -> BaseResponse[ProjectDetailsResponse]:
        with self.get_session() as db:
            project = db.query(ProjectModel).filter(ProjectModel.id == project_id and creator_user_id == creator_user_id).first()
            if not project:
                return BaseResponse(
                    statusCode=status.HTTP_400_BAD_REQUEST,
                    message="Project not found",
                    data=None
                )
            
            project_response = ProjectResponse(
                id=project.id,
                title=project.title,
                description=project.description,
                start_date=project.start_date,
                end_date=project.end_date,
                state=self.get_project_status(project)
            )
            team_members = db.query(ProjectMemberModel).filter(ProjectMemberModel.project_id == project_id).all()
            checkin_details = db.query(CheckinModel).filter(CheckinModel.project_id == project_id).first()

            #get current time in UTC
            date_usertz = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=int(checkin_details.user_timezone))))
            checkin_responses = db.query(CheckInResponseModel).filter(CheckInResponseModel.project_id == project_id and date_usertz.date == date_usertz.date).all()

            checkin_response_details = [
                CheckInResponse(
                    id=response.id,
                    project_id=response.project_id,
                    team_member_id=response.team_member_id,
                    date_usertz=response.date_usertz,
                    date_utctz=response.date_utctz,
                    did_yesterday=response.did_yesterday,
                    doing_today=response.doing_today,
                    blockers=response.blocker
                ) for response in checkin_responses
            ]

            members = [
                ProjectMemberResponse(
                    id=member.id,
                    user_email=member.user_email,
                    is_creator=member.is_creator
                ) for member in team_members
            ]
            project_response = ProjectDetailsResponse(
                id=project.id,
                title=project.title,
                description=project.description,
                start_date=project.start_date,
                end_date=project.end_date,
                state=self.get_project_status(project),
                checkin_time=checkin_details.user_checkin_time.strftime("%H:%M"),
                checkin_days=checkin_details.user_checkin_days.strip('{}').split(','),
                members= members,
                timezone=checkin_details.user_timezone,
                checkin_responses=checkin_response_details
            )
            return BaseResponse(
                statusCode=status.HTTP_200_OK,
                message="Project found",
                data=project_response
            )