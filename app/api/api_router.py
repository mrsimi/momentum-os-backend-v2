from fastapi import APIRouter
from app.api.endpoints import auth_endpoint, project_endpoint

api_router = APIRouter()
api_router.include_router(auth_endpoint.router, prefix="/user", tags=["auth"])
api_router.include_router(project_endpoint.router, prefix="/projects", tags=["project"])