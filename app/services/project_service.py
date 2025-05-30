from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import logging
import os
from sqlalchemy.sql import func
from app.core.database import SessionLocal
from sqlalchemy import extract

from app.infra.email_infra import EmailInfra
from app.models.project_model import CheckinModel, ProjectMemberModel, ProjectModel
from app.models.response_model import CheckInResponseModel
from app.models.subscription_model import UserSubscriptionModel
from app.models.user_model import UserModel
from app.schemas.checkin_response_schema import CheckInResponse
from app.schemas.project_schema import EnableDisableTeamMemberRequest, NewMemberRequest, ProjectAnalyticsResponse, ProjectDashboardResponse, ProjectDetailsResponse, ProjectMemberResponse, ProjectRequest, ProjectResponse, SendInvitationRequest
from app.schemas.response_schema import BaseResponse
from app.services.subscription_service import SubscriptionService
from app.utils.helpers import convert_utc_days_and_time
from sqlalchemy.exc import IntegrityError

from fastapi import status

from app.utils.security import decrypt_payload, encrypt_payload

logging.basicConfig(
    format="%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
    level=logging.INFO
)

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
            project_request.members_emails = [email.lower().strip() for email in project_request.members_emails]
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
                
                #get user subscription and check if they can create project
                user_sub = SubscriptionService().get_user_subscription(user_id, db=db)

                now = datetime.now(timezone.utc)
                current_year = now.year
                current_month = now.month

                months_projects = db.query(ProjectModel).filter(
                    ProjectModel.creator_user_id == user_id,
                    extract('year', ProjectModel.date_created) == current_year,
                    extract('month', ProjectModel.date_created) == current_month
                ).count()

                added_members = len(project_request.members_emails)

                if user_sub.data.plan_id == 0:
                    # Free plan limits
                    if months_projects >= 3:
                        return BaseResponse(
                            statusCode=status.HTTP_400_BAD_REQUEST,
                            message="You have reached the maximum number of projects for this month. Please upgrade your plan to create more projects.",
                            data=None
                        )
                    if added_members > 3:
                        return BaseResponse(
                            statusCode=status.HTTP_400_BAD_REQUEST,
                            message="Free plan allows a maximum of 3 members per project. Please reduce team size or upgrade your plan.",
                            data=None
                        )
                elif user_sub.data.plan_id == 1:
                    # Basic plan limits
                    if months_projects >= 10:
                        return BaseResponse(
                            statusCode=status.HTTP_400_BAD_REQUEST,
                            message="You have reached the maximum number of projects for this month. Kindly contact customer care to upgrade your plan.",
                            data=None
                        )
                    if added_members > 10:
                        return BaseResponse(
                            statusCode=status.HTTP_400_BAD_REQUEST,
                            message="Basic plan allows a maximum of 10 members per project. Please reduce team size or upgrade your plan.",
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
                    user_email=member.email.lower().strip()
                ) for member in members_already_user)

                list_of_members.extend(ProjectMemberModel(
                    project_id=project.id,
                    user_id=None,
                    is_active=False,
                    is_creator=False,
                    is_guest=True,
                    is_member=False,
                    user_email=email.lower().strip()
                ) for email in members_not_users)

                list_of_members.append(ProjectMemberModel(
                    project_id=project.id,
                    user_id=user_id,
                    is_active=True,
                    is_creator=True,
                    is_guest=False,
                    is_member=True,
                    user_email=user.email.lower().strip(),
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
            logging.info(f"Error creating project: {e}")
            return BaseResponse(
                statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Internal server error",
                data=None
            )

    def get_project_analytics(self, projects:list[ProjectModel]) -> tuple:
        now = datetime.now()

        # Determine last month and its year
        if now.month == 1:
            last_month = 12
            last_month_year = now.year - 1
        else:
            last_month = now.month - 1
            last_month_year = now.year

        # Get projects for this month
        this_month_projects = [
            p for p in projects
            if p.start_date.month == now.month and p.start_date.year == now.year and p.is_active
        ]

        # Get projects for last month
        last_month_projects = [
            p for p in projects
            if p.start_date.month == last_month and p.start_date.year == last_month_year and p.is_active
        ]

        return (len(this_month_projects), len(last_month_projects))

    def get_projects_by_creator_id(self, user_id:int) -> BaseResponse[ProjectDashboardResponse]:
        projects_response = None
        now = datetime.now()
        try:
            with self.get_session() as db:
                projects = db.query(ProjectModel).filter(ProjectModel.creator_user_id == user_id).all()
                if not projects:
                    return BaseResponse(
                        statusCode=status.HTTP_200_OK,
                        message="No Projects found",
                        data= ProjectDashboardResponse(projects=[], analytics=ProjectAnalyticsResponse(
                            active_projects=0,
                            team_members=0,
                            submitted_responses=0,
                            active_projects_last_month=0
                        ))
                    )
                
                this_month, last_month = self.get_project_analytics(projects)
                team_members = db.query(ProjectMemberModel).filter(
                    extract('month', ProjectMemberModel.date_created) == now.month,
                    extract('year', ProjectMemberModel.date_created) == now.year,
                    ProjectMemberModel.is_active == True
                ).count()
                
                submitted_response = db.query(CheckInResponseModel).filter(
                    extract('month', CheckInResponseModel.checkin_date_usertz) == now.month,
                    extract('year', CheckInResponseModel.checkin_date_usertz) == now.year
                ).count()
                
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
                data= ProjectDashboardResponse (projects=projects_response, 
                                                analytics= ProjectAnalyticsResponse(
                                                    active_projects=this_month, 
                                                    team_members=team_members,
                                                    submitted_responses=submitted_response,
                                                    active_projects_last_month=last_month))
            )
        except Exception as e:
            logging.info(f'Error while get_projects_by_creator_id response {e}')

            if projects_response:
                return BaseResponse(
                    statusCode=status.HTTP_200_OK,
                    message="Project found",
                    data= ProjectDashboardResponse (projects=projects_response, 
                                                    analytics=ProjectAnalyticsResponse(
                            active_projects=0,
                            team_members=0,
                            submitted_responses=0,
                            active_projects_last_month=0
                        ))
                                            )

            return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Error while trying to get project",
                        data=None
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
            

            subscription = SubscriptionService()
            creator_user_sub = subscription.get_user_subscription(project.creator_user_id, db)
            active_team_members = db.query(ProjectMemberModel).filter(ProjectMemberModel.project_id == project_id, 
                                                                      ProjectMemberModel.is_active == True,
                                                                      ProjectMemberModel.is_creator == False).all()
            
            print(active_team_members)
            print(creator_user_sub.data)
            
            if not self.can_add_members(creator_user_sub.data.plan_id, len(active_team_members)):
                return BaseResponse(
                    statusCode=status.HTTP_400_BAD_REQUEST,
                    message="Cannot join project, User already exhausted number of active members. Contact Project owner to upgrade subscription",
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
            project_member.has_rejected = False
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

            #get current time in UTC and convert it to user timezone
            date_usertz = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=int(checkin_details.user_timezone))))
            should_have_checkin = False

            checkin_days_utc = checkin_details.user_checkin_days  # Already a list
            current_day = date_usertz.strftime("%A")

            should_have_checkin = current_day in checkin_days_utc

            logging.info(checkin_days_utc)
            logging.info(current_day)



            checkin_responses = db.query(CheckInResponseModel).filter(CheckInResponseModel.project_id == project_id, 
                                                                      func.date(CheckInResponseModel.checkin_date_usertz) == date_usertz.date()).all()

            checkin_response_details = [
                CheckInResponse(
                    id=response.id,
                    project_id=response.project_id,
                    team_member_id=response.team_member_id,
                    checkin_date_usertz=response.checkin_date_usertz,
                    did_yesterday=response.did_yesterday,
                    doing_today=response.doing_today,
                    blockers=response.blocker
                ) for response in checkin_responses
            ]

            members = [
                ProjectMemberResponse(
                    id=member.id,
                    user_email=member.user_email,
                    is_creator=member.is_creator,
                    has_accepted=member.has_accepted,
                    has_rejected=member.has_rejected,
                    is_guest=member.is_guest,
                    is_active=member.is_active
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
                checkin_days=checkin_details.user_checkin_days,
                members= members,
                timezone=checkin_details.user_timezone,
                checkin_responses=checkin_response_details,
                should_have_checkin = should_have_checkin
            )
            return BaseResponse(
                statusCode=status.HTTP_200_OK,
                message="Project found",
                data=project_response
            )
    
    def get_projects_by_public(self, project_id:int):
        try:
            with self.get_session() as db:
                project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
                if not project:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Project not found",
                        data=None
                    )

                response_data = ProjectResponse(
                    id=project.id,
                    title=project.title,
                    description=project.description,
                    start_date=project.start_date,
                    end_date=project.end_date,
                    state= self.get_project_status(project)
                )

                return BaseResponse(
                        statusCode=status.HTTP_200_OK,
                        message="success",
                        data=response_data
                    )
        except Exception as e:
            logging.info(f'Error while get_projects_by_public response {e}')
            return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Error while trying to get project",
                        data=None
                    )

    #allow edit of name, description, start and end date and checkin time 
    def edit_project(self, project_request:ProjectRequest, user_id:int, project_id: int) -> BaseResponse[str]:
        try:
            with self.get_session() as db:
                project = db.query(ProjectModel).filter(ProjectModel.id == project_id,
                                                           ProjectModel.creator_user_id == user_id).first()
                if not project:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Project not found",
                        data=None
                    )
                
                if not project.is_active:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Project is no longer active.",
                        data=None
                    )
                
                checkin = db.query(CheckinModel).filter(CheckinModel.project_id == project_id).first()
                if not checkin:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Checkin does not exist for the project. Kindly contact customer care",
                        data=None
                    )
                
                checkin_days_utc, checkin_time_utc = convert_utc_days_and_time(project_request.checkin_days,
                                                        project_request.checkin_time,
                                                        project_request.timezone)
                
                
                project.title = project_request.title
                project.description = project_request.description
                project.start_date = project_request.start_date
                project.end_date = project_request.end_date
                project.date_updated = datetime.now(timezone.utc)

                checkin.user_checkin_days = project_request.checkin_days
                checkin.user_checkin_time = project_request.checkin_time
                checkin.user_timezone = project_request.timezone
                checkin.checkin_time_utc=checkin_time_utc,
                checkin.checkin_days_utc = checkin_days_utc

                db.commit()

                return BaseResponse(
                        statusCode=status.HTTP_200_OK,
                        message="Project successfully updated",
                        data=None
                    )

                    

        except Exception as e:
            logging.info(f'Error while get_projects_by_public response {e}')
            return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Error while trying to get project",
                        data=None
                    )
    
    def disable_member_from_project(self, user_id: int, request:EnableDisableTeamMemberRequest) -> BaseResponse[str]:
        try:
            with self.get_session() as db:
                user_project = db.query(ProjectModel).filter(ProjectModel.id== request.project_id, 
                                                             ProjectModel.is_active == True, 
                                                             ProjectModel.creator_user_id == user_id).first()
                if not user_project:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Project not found for user",
                        data=None
                    )
                
                member = db.query(ProjectMemberModel).filter(ProjectMemberModel.project_id == request.project_id,
                                                             ProjectMemberModel.id == request.member_id).first()
                if not member:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Member not valid for this project",
                        data=None
                    )
                
                #1- disable, 2 - enable
                if request.action == 1:
                    member.is_active = False
                    member.date_updated = datetime.now(timezone.utc)
                elif request.action == 2:
                    active_members = db.query(ProjectMemberModel).filter(ProjectMemberModel.project_id == request.project_id,
                                                                   ProjectMemberModel.is_active == True,
                                                                   ProjectMemberModel.is_creator == False).all()
                    creator_subscription = SubscriptionService().get_user_subscription(user_id, db)
                    if not self.can_add_members(creator_subscription.data.plan_id, len(active_members)):
                        return BaseResponse(
                            statusCode=status.HTTP_400_BAD_REQUEST,
                            message=f"Cannot have more than {len(active_members)} active members for your current plan. Kindly upgrade or contact administrator",
                            data=None
                        )

                    member.is_active = True
                    member.date_updated = datetime.now(timezone.utc)

                db.commit()

                return BaseResponse(
                        statusCode=status.HTTP_200_OK,
                        message="Team member status successfully updated",
                        data=None
                    )
        except Exception as e:
            logging.info(f'Error remove_member_from_project response {e}')
            return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Error while update team member status",
                        data=None
                    )
        
    def add_new_member(self, user_id:int, request:NewMemberRequest) -> BaseResponse[str]:
        try:
            with self.get_session() as db:
                creator = db.query(UserModel).filter(UserModel.id == user_id).first()
                if not creator:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Not a valid user",
                        data=None
                    )
                
                if creator.email == request.email.lower().strip():
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Cannot add project creator again",
                        data=None
                    )
                project = db.query(ProjectModel).filter(ProjectModel.creator_user_id == user_id, 
                                                        ProjectModel.id == request.project_id, 
                                                        ProjectModel.is_active == True).first()
                if not project:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Active project not found",
                        data=None
                    )
                
                team_member_with_email = db.query(ProjectMemberModel).filter(ProjectMemberModel.user_email == 
                                                                             request.email.lower().strip()).first()
                if team_member_with_email:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="User with email already part of team",
                        data=None
                    )

                team_members = db.query(ProjectMemberModel).filter(ProjectMemberModel.project_id == project.id,
                                                                   ProjectMemberModel.is_active == True,
                                                                   ProjectMemberModel.is_creator == False).all()
                
                
                if team_members:
                    subscription  = SubscriptionService()
                    user_sub = subscription.get_user_subscription(user_id, db)

                    if not self.can_add_members(user_sub.data.plan_id, len(team_members)):
                        return BaseResponse(
                            statusCode=status.HTTP_400_BAD_REQUEST,
                            message=f"Cannot add more than {len(team_members)} active members for your current plan. Kindly upgrade or contact administrator",
                            data=None
                        )
                
                
                member_user = db.query(UserModel).filter(UserModel.email == request.email.lower().strip()).first()
                member = ProjectMemberModel(
                            project_id=project.id,
                            user_id=member_user.id if member_user else None,
                            is_active=False,
                            is_creator=False,
                            is_guest=not member_user,
                            is_member=bool(member_user),
                            user_email=request.email
                        )

                db.add(member)
                db.commit()

                #send email to all members who are not users.
                self.send_emails_to_members([request.email]
                                            , project.title, project.id, creator.email)
                
                return BaseResponse(
                        statusCode=status.HTTP_200_OK,
                        message="Member added and Email has been sent",
                        data=None
                    )



        except Exception as e:
            logging.info(f'Error add_new_member response {e}')
            return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Error while trying to add member to project",
                        data=None
                    ) 
    
    def can_add_members(self, subcription_plan, current_members_count):
        if subcription_plan == 0 and current_members_count >= 3:
            return False
        elif subcription_plan == 1 and current_members_count >= 10:
            return False
        return True
    
    def send_invitation_link(self, user_id:int, request:SendInvitationRequest) -> BaseResponse[str]:
        try:
            with self.get_session() as db:
                project = db.query(ProjectModel).filter(ProjectModel.id == request.project_id, 
                                                        ProjectModel.creator_user_id == user_id).first()
                if not project:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Project not found",
                        data=None
                    )
                
                active_members = db.query(ProjectMemberModel).filter(ProjectMemberModel.project_id == request.project_id,
                                                                   ProjectMemberModel.is_active == True,
                                                                   ProjectMemberModel.is_creator == False).all()
                
                creator_subscription = SubscriptionService().get_user_subscription(user_id, db)
                if not self.can_add_members(creator_subscription.data.plan_id, len(active_members)):
                    return BaseResponse(
                            statusCode=status.HTTP_400_BAD_REQUEST,
                            message=f"Cannot have more than {len(active_members)} active members for your current plan. Kindly upgrade or contact administrator",
                            data=None
                        )
                
                creator = db.query(UserModel).filter(UserModel.id == user_id).first()
                member_user = db.query(ProjectMemberModel).filter(ProjectMemberModel.id == request.member_id).first()
                if member_user.is_active:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Member is already an active participant in the project",
                        data=None
                    )
                
                self.send_emails_to_members([member_user.user_email]
                                            , project.title, project.id, creator.email)
                
                return BaseResponse(
                        statusCode=status.HTTP_200_OK,
                        message="Invitation link sent again",
                        data=None
                    )
                


        except Exception as e:
            logging.info(f'Error send_invitation_link response {e}')
            return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Error while trying to add member to project",
                        data=None
                    ) 