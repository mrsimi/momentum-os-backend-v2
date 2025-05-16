from datetime import date
from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from app.schemas.checkin_response_schema import CheckInAnalyticsResponse, GenerateSummaryRequest, SendCheckInReminderRequest, SubmitCheckInRequest
from app.schemas.response_schema import BaseResponse
from app.services.response_service import ResponseService
from app.utils.auth_bearer import JWTBearer
from app.utils.logged_route import LoggedRoute

router = APIRouter(
    prefix="/checkin-response",
    tags=["checkin-response"]
)

router.route_class = LoggedRoute

@router.post('/', response_model=BaseResponse[str])
def submit_checkin(request:SubmitCheckInRequest):
    project_service = ResponseService()
    response = project_service.submit_checkin(request)
    return JSONResponse(status_code=response.statusCode, content=response.dict())


@router.get('/', response_model=BaseResponse[CheckInAnalyticsResponse])
def get_check_analytics(project_id:int=Query(...), checkin_date:date=Query(...)):
    project_service = ResponseService()
    response = project_service.get_check_analytics(project_id, checkin_date)
    return JSONResponse(status_code=response.statusCode, content=jsonable_encoder(response))


@router.post('/generate-summary', response_model=BaseResponse[CheckInAnalyticsResponse])
def generate_summary(request:GenerateSummaryRequest, payload: dict = Depends(JWTBearer())):
    project_service = ResponseService()
    response = project_service.generate_checkin_summary(request)
    return JSONResponse(status_code=response.statusCode, content=jsonable_encoder(response))


@router.get('/trends')
def get_trends(payload:dict = Depends(JWTBearer())):
    response_service = ResponseService()
    user_id = payload.get("user_id")
    response = response_service.get_trends(user_id)
    return JSONResponse(status_code=response.statusCode, content=jsonable_encoder(response))

@router.get('/generate-blog')
def generate_blog():
    return 

@router.post('/send-reminder', response_model=BaseResponse[str])
def send_reminder(request:SendCheckInReminderRequest, payload:dict = Depends(JWTBearer())):
    response_service = ResponseService()
    user_id = payload.get("user_id")
    request.creator_user_id = user_id
    response = response_service.send_reminder(request)
    return JSONResponse(status_code=response.statusCode, content=jsonable_encoder(response))