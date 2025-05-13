from datetime import date
from fastapi import APIRouter, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from app.schemas.checkin_response_schema import CheckInAnalyticsResponse, GenerateSummaryRequest, SubmitCheckInRequest
from app.schemas.response_schema import BaseResponse
from app.services.response_service import ResponseService
from app.utils.logged_route import LoggedRoute

router = APIRouter(
    prefix="/checkin-reponse",
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
def generate_summary(request:GenerateSummaryRequest):
    project_service = ResponseService()
    response = project_service.generate_checkin_summary(request)
    return JSONResponse(status_code=response.statusCode, content=jsonable_encoder(response))

