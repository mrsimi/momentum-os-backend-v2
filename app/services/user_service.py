from datetime import datetime, timezone
import logging
import httpx
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.project_model import ProjectMemberModel
from app.models.user_model import UserModel
from app.core.database import SessionLocal
from typing import Optional
from contextlib import contextmanager
from app.utils.security import check_password, create_access_token, generate_encrypted_user_id, hash_password, decrypt_encrypted_user_id

from app.schemas.auth_schema import GoogleLoginRequest, LoginRequest, RegisterRequest
from app.schemas.response_schema import BaseResponse
from app.infra.email_infra import EmailInfra

from fastapi import status

import os
logging.basicConfig(
    format="%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
    level=logging.INFO
)

class UserService:
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

    def register(self, register_request: RegisterRequest) -> BaseResponse[str]:
       
        with self.get_session() as db:
            user = self.get_user_by_email(register_request.email, db)
            if user:
                return BaseResponse(
                    statusCode=status.HTTP_400_BAD_REQUEST,
                    message="User already exists",
                    data=None
                )
            else:
                hashed_password = hash_password(register_request.password.strip())
                db_user = UserModel(
                    email=register_request.email.lower().strip(),
                    hashed_password=hashed_password,
                    is_active=True,
                    is_guest=False
                )
                db.add(db_user)
                db.commit()
                db.refresh(db_user)
                self.completed_user_profile_in_team_members(db_user.email, db, db_user.id)
                self.send_verify_email(db_user.id, db_user.email)

                return BaseResponse(
                    statusCode=status.HTTP_200_OK,
                    message="User created successfully",
                    data=db_user.id
                )
            
    def verify_email(self, token: str) -> BaseResponse[str]:
        try:
            user_id = decrypt_encrypted_user_id(token)
            with self.get_session() as db:
                user = self.get_user_by_user_id(user_id, db)
                if user:
                        user.is_verified = True
                        user.date_updated = datetime.now(timezone.utc)
                        db.commit()
                        db.refresh(user)
                        
                        access_token = create_access_token(user.id)

                        return BaseResponse(
                            statusCode=status.HTTP_200_OK,
                            message="Email verified successfully",
                            data= { "user_id": user.id, "access_token": access_token }
                        )
                else:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="User not found",
                        data=None
                    )
        except Exception as e:
            logging.info(e)
            return BaseResponse(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="Invalid token",
                data=None
            )
    
    def login(self, login_request: LoginRequest) -> BaseResponse[str]:
        try:
            with self.get_session() as db:
                user = self.get_user_by_email(login_request.email, db)
                if user is None:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="User not found",
                        data=None
                    )
                
                if user.is_verified == False:
                    self.send_verify_email(user.id, user.email)
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Email not verified, kindly click on the link in your email to verify your account",
                        data=None
                    )
                
                if not user.hashed_password:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Invalid login, kindly use google login",
                        data=None
                    )
                if user:
                    if check_password(login_request.password.strip(), user.hashed_password):
                        access_token = create_access_token(user.id)
                        user.last_login = datetime.now(timezone.utc)
                        db.commit()
                        db.refresh(user)
                        return BaseResponse(
                            statusCode=status.HTTP_200_OK,
                            message="Login successful",
                            data= { "user_id": user.id, "access_token": access_token }
                        )
                    else:
                        return BaseResponse(
                            statusCode=status.HTTP_400_BAD_REQUEST,
                            message="Invalid password",
                            data=None
                        )
                else:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="User not found",
                        data=None
                    )
        except Exception as e:
            logging.error('Error on login', e)
            return BaseResponse(
                            statusCode=status.HTTP_400_BAD_REQUEST,
                            message="An error occured while trying to login",
                            data=None
                        )
    
    def forgot_password(self, email: str) -> BaseResponse[str]:
        with self.get_session() as db:
            user = self.get_user_by_email(email, db)
            if user:
                self.send_reset_password_email(user.id, user.email)
                return BaseResponse(
                    statusCode=status.HTTP_200_OK,
                    message="Password reset email sent",  
                    data=None
                )
            else:
                return BaseResponse(
                    statusCode=status.HTTP_400_BAD_REQUEST,
                    message="User not found",
                    data=None
                )
            
    def update_password_change_process(self, token: str) -> BaseResponse[str]:
        user_id = decrypt_encrypted_user_id(token)
        with self.get_session() as db:
            user = self.get_user_by_user_id(user_id, db)
            if user:
                user.to_changePassword = True
                db.commit()
                db.refresh(user)
                return BaseResponse(
                    statusCode=status.HTTP_200_OK,
                    message="Success",  
                    data=None
                )
            else:
                return BaseResponse(
                    statusCode=status.HTTP_400_BAD_REQUEST,
                    message="Invalid link",
                    data=None
                )
    
    def update_password(self, token: str, password: str) -> BaseResponse[str]:
        user_id = decrypt_encrypted_user_id(token)
        with self.get_session() as db:
            user = self.get_user_by_user_id(user_id, db)
            if user and user.to_changePassword:
                user.hashed_password = hash_password(password.strip())
                user.to_changePassword = False
                user.date_updated = datetime.now(timezone.utc)

                db.commit()
                db.refresh(user)
                return BaseResponse(
                    statusCode=status.HTTP_200_OK,
                    message="Password updated successfully",
                    data=None
                )
            else:
                return BaseResponse(
                    statusCode=status.HTTP_400_BAD_REQUEST,
                    message="Invalid User",
                    data=None
                )    
                    
    def get_user_by_email(self, email: str, db:Session) -> Optional[UserModel]:
        return db.query(UserModel).filter(UserModel.email == email.lower().strip()).first()
    
    def get_user_by_user_id(self, id: int, db:Session) -> Optional[UserModel]:
        return db.query(UserModel).filter(UserModel.id == id).first()

    def send_verify_email(self, user_id: int, email: str):
        verify_email_link = generate_encrypted_user_id(user_id)
        email_infra = EmailInfra()

        # send email verification
        email_infra.send_email(
            destinationEmail=email,
            subject="Rava Verify your email",
            type="verify_email",
            object={
                "link": f"{os.getenv('FRONTEND_URL')}/click?upnv={verify_email_link}"
            }
        )
    def send_reset_password_email(self, user_id: int, email: str):
        reset_password_link = generate_encrypted_user_id(user_id)
        email_infra = EmailInfra()
        email_infra.send_email(
            destinationEmail=email,
            subject="Rava Reset your password",
            type="reset_password",
            object={
                "link": f"{os.getenv('FRONTEND_URL')}/click?upnp={reset_password_link}"
            }
        )

    def google_auth(self, request:GoogleLoginRequest):
        try:
            with httpx.Client() as client:
                response = client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {request.token}"}
                )

                if response.status_code != 200:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Could not verify google sign in",
                        data=None
                    )

            user_info = response.json()
            email = user_info['email']
            externalsignup_id = user_info['sub']

            with self.get_session() as db:
                user = db.query(UserModel).filter(
                        or_(
                            UserModel.email == email.lower().strip(),
                            UserModel.externalsignup_id == externalsignup_id
                        )
                    ).first()

                
                if not user:
                    #register user
                    db_user = UserModel(
                        email=email.lower().strip(),
                        is_active=True,
                        is_guest=False,
                        is_verified = True,
                        externalsignup_id = externalsignup_id,
                        externalsignupprovider = 'GOOGLE'
                    )
                    db.add(db_user)
                    db.commit()
                    db.refresh(db_user)

                    self.completed_user_profile_in_team_members(db_user.email, db, db_user.id)
                    res_access_token = create_access_token(db_user.id)

                    return BaseResponse(
                            statusCode=status.HTTP_200_OK,
                            message="Login successful",
                            data= { "user_id": db_user.id, "access_token": res_access_token }
                        )
                else:
                    if user.hashed_password:
                        return BaseResponse(
                            statusCode=status.HTTP_400_BAD_REQUEST,
                            message="Kindy continue with your email and password",
                            data=None
                        )
                    if user.externalsignup_id:
                        #sign in user
                        access_token = create_access_token(user.id)
                        user.last_login = datetime.now(timezone.utc)
                        db.commit()
                        db.refresh(user)
                        return BaseResponse(
                            statusCode=status.HTTP_200_OK,
                            message="Login successful",
                            data= { "user_id": user.id, "access_token": access_token }
                        )
                
            
        except Exception as e:
            logging.error('Error on signin with google ', e)
            return BaseResponse(
                            statusCode=status.HTTP_400_BAD_REQUEST,
                            message="An error occured while trying to login with google",
                            data=None
                        )
    
    def completed_user_profile_in_team_members(self, email, db:Session, user_id:int):
        db.query(ProjectMemberModel).filter(ProjectMemberModel.user_email == email
                                            ).update({ProjectMemberModel.user_id: user_id, 
                                                      ProjectMemberModel.is_member:True,
                                                       ProjectMemberModel.is_guest:False }, synchronize_session="auto")
        db.commit()
