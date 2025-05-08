from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.schemas.checkin_response_schema import SubmitCheckInRequest
from app.schemas.response_schema import BaseResponse
from app.services.response_service import ResponseService

router = APIRouter(
    prefix="/checkin-reponse",
    tags=["checkin-response"]
)


@router.post('/', response_model=BaseResponse[str])
async def submit_checkin(request:SubmitCheckInRequest):
    project_service = ResponseService()
    response = await project_service.submit_checkin(request)
    return JSONResponse(status_code=response.statusCode, content=response.dict())