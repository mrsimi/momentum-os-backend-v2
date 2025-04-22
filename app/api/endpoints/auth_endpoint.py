from fastapi import APIRouter, Query
from app.schemas.auth_schema import ForgotPasswordRequest, LoginRequest, RegisterRequest, UpdatePasswordRequest
from app.schemas.response_schema import BaseResponse
from app.services import UserService
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/register", response_model=BaseResponse[str])
async def register(request: RegisterRequest):
    user_service = UserService()
    response = user_service.register(request)
    return JSONResponse(status_code=response.statusCode, content=response.dict())

#after verify redirect users to login page.
@router.post("/verify-email", response_model=BaseResponse[str])
async def verify_email(token: str = Query(...)):
    user_service = UserService()
    response = user_service.verify_email(token)
    return JSONResponse(status_code=response.statusCode, content=response.dict())

@router.post("/login", response_model=BaseResponse[str])
async def login(request: LoginRequest):
    user_service = UserService()
    response = user_service.login(request)
    return JSONResponse(status_code=response.statusCode, content=response.dict())

@router.post("/forgot-password", response_model=BaseResponse[str])
async def forgot_password(request: ForgotPasswordRequest):
    user_service = UserService()
    response = user_service.forgot_password(request.email)
    return JSONResponse(status_code=response.statusCode, content=response.dict())

@router.post("/forgot-password-link", response_model=BaseResponse[str])
async def update_password_change_process(token: str = Query(...)):
    user_service = UserService()
    response = user_service.update_password_change_process(token)
    return JSONResponse(status_code=response.statusCode, content=response.dict())

@router.post("/update-password", response_model=BaseResponse[str])
async def update_password(request: UpdatePasswordRequest):
    user_service = UserService()
    response = user_service.update_password(request.token, request.password)
    return JSONResponse(status_code=response.statusCode, content=response.dict())





