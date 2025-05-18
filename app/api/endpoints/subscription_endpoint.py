from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, RedirectResponse

from app.schemas.response_schema import BaseResponse
from app.services.subscription_service import SubscriptionService
from app.utils.auth_bearer import JWTBearer
from app.utils.logged_route import LoggedRoute


router = APIRouter(
    prefix="/subscription",
    tags=["subscription"]
)

router.route_class = LoggedRoute

@router.post('', response_model=BaseResponse[str])
def subscribe(payload: dict = Depends(JWTBearer())):
    user_id = payload.get('user_id')
    subscriptionService = SubscriptionService()
    res = subscriptionService.subscribe_to_plan(user_id)
    return JSONResponse(status_code=res.statusCode, content=jsonable_encoder(res))

@router.post('/webhook', response_model=BaseResponse[str])
def webhook(payload:dict):
    subscriptionService = SubscriptionService()
    res = subscriptionService.save_webhook_data(payload)
    return JSONResponse(status_code=res.statusCode, content=jsonable_encoder(res))
