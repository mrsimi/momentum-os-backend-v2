from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer

from app.schemas.project_schema import ProjectDetailsResponse, ProjectRequest, ProjectResponse
from app.schemas.response_schema import BaseResponse
from app.services.project_service import ProjectService
from fastapi.encoders import jsonable_encoder

from app.utils.auth_bearer import JWTBearer

router = APIRouter(
    prefix="/projects",
    tags=["projects"]
)


@router.post("", response_model=BaseResponse[str])
def create_project(request: ProjectRequest, payload: dict = Depends(JWTBearer())):
    user_id = payload.get("user_id")
    project_service = ProjectService()
    response = project_service.create_project(request, user_id)
    return JSONResponse(status_code=response.statusCode, content=response.dict())

@router.post("/invitation-response", response_model=BaseResponse[str])
def submit_project_invite_response(url:str =Query(...)):
    project_service = ProjectService()
    response = project_service.submit_project_invite_response(url)
    return JSONResponse(status_code=response.statusCode, content=response.dict())

@router.get("", response_model=BaseResponse[list[ProjectResponse]])
def get_projects_by_creator_id(payload: dict = Depends(JWTBearer())):
    user_id = payload.get("user_id")
    project_service = ProjectService()
    response = project_service.get_projects_by_creator_id(user_id)
    return JSONResponse(status_code=response.statusCode, content=jsonable_encoder(response))

@router.get("/projects", response_model=BaseResponse[ProjectDetailsResponse])
def get_project_by_id(project_id: int, payload: dict = Depends(JWTBearer())):
    project_service = ProjectService()
    response = project_service.get_project_details(project_id)
    return JSONResponse(status_code=response.statusCode, content=jsonable_encoder(response))

@router.put("/deactivate", response_model=BaseResponse[str])
def deactivate_project(project_id: int, payload: dict = Depends(JWTBearer())):
    user_id = payload.get("user_id")
    project_service = ProjectService()
    response = project_service.deactivate_project(project_id, user_id)
    return JSONResponse(status_code=response.statusCode, content=response.dict())

@router.put("/complete", response_model=BaseResponse[str])
def deactivate_project(project_id: int, payload: dict = Depends(JWTBearer())):
    user_id = payload.get("user_id")
    project_service = ProjectService()
    response = project_service.complete_project(project_id, user_id)
    return JSONResponse(status_code=response.statusCode, content=response.dict())
