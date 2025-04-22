from fastapi import APIRouter
from app.api.endpoints import auth_endpoint

api_router = APIRouter()
api_router.include_router(auth_endpoint.router, prefix="/auth", tags=["auth"])