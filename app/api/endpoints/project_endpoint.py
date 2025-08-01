from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.schemas.project_schema import  EnableDisableTeamMemberRequest, NewMemberRequest, ProjectDashboardResponse, ProjectDetailsResponse, ProjectRequest, ProjectResponse, SendInvitationRequest
from app.schemas.response_schema import BaseResponse
from app.services.project_service import ProjectService
from fastapi.encoders import jsonable_encoder

from app.utils.auth_bearer import JWTBearer
from app.utils.logged_route import LoggedRoute

router = APIRouter(
    prefix="/projects",
    tags=["projects"]
)

router.route_class = LoggedRoute

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

@router.get("", response_model=BaseResponse[ProjectDashboardResponse])
def get_projects_by_creator_id(payload: dict = Depends(JWTBearer())):
    user_id = payload.get("user_id")
    project_service = ProjectService()
    response = project_service.get_projects_by_creator_id(user_id)
    return JSONResponse(status_code=response.statusCode, content=jsonable_encoder(response))

@router.get("/{project_id}", response_model=BaseResponse[ProjectDetailsResponse])
def get_project_by_id(project_id: int, payload: dict = Depends(JWTBearer())):
    project_service = ProjectService()
    user_id = payload.get("user_id")
    response = project_service.get_project_details(project_id, user_id)
    return JSONResponse(status_code=response.statusCode, content=jsonable_encoder(response))

@router.get("/public/{project_id}", response_model=BaseResponse[ProjectResponse])
def get_project_by_id(project_id: int):
    project_service = ProjectService()
    response = project_service.get_projects_by_public(project_id)
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

@router.put("/{project_id}", response_model=BaseResponse[str])
def edit_project(request:ProjectRequest, project_id:int, payload:dict= Depends(JWTBearer())):
    user_id = payload.get("user_id")
    project_service = ProjectService()
    response = project_service.edit_project(project_request=request, user_id=user_id,  project_id=project_id)
    return JSONResponse(status_code=response.statusCode, content=response.dict())

@router.put("/member/status", response_model=BaseResponse[str])
def edit_team_member_status(request: EnableDisableTeamMemberRequest, payload:dict=Depends(JWTBearer())):
    user_id = payload.get("user_id")
    project_service = ProjectService()
    response = project_service.disable_member_from_project(user_id, request)
    return JSONResponse(status_code=response.statusCode, content=response.dict())

@router.post("/new-member", response_model=BaseResponse[str])
def add_new_member(request: NewMemberRequest, payload:dict=Depends(JWTBearer())):
    user_id = payload.get("user_id")
    project_service = ProjectService()
    response = project_service.add_new_member(user_id, request)
    return JSONResponse(status_code=response.statusCode, content=response.dict())

@router.post("/invite", response_model=BaseResponse[str])
def send_invite_link(request:SendInvitationRequest, payload:dict=Depends(JWTBearer())):
    user_id = payload.get("user_id")
    project_service = ProjectService()
    response = project_service.send_invitation_link(user_id, request)
    return JSONResponse(status_code=response.statusCode, content=response.dict())




