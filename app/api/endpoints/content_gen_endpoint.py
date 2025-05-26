from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.schemas.checkin_response_schema import GenerateContentRequest
from app.schemas.response_schema import BaseResponse
from app.services.content_gen_service import ContentGenerationService
from app.services.subscription_service import SubscriptionService
from app.utils.auth_bearer import JWTBearer
from app.utils.logged_route import LoggedRoute


router = APIRouter(
    prefix="/content-gen",
    tags=["content-gen"]
)

router.route_class = LoggedRoute

@router.post('', response_model=BaseResponse[str])
def subscribe(request:GenerateContentRequest, payload: dict = Depends(JWTBearer())):
    user_id = payload.get('user_id')
    content_gen_service = ContentGenerationService()
    res = content_gen_service.generate_content(request.checkin_dates, request.project_id, user_id)
    return JSONResponse(status_code=res.statusCode, content=jsonable_encoder(res))


