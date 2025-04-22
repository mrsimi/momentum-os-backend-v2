from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import status
import traceback

from app.schemas.response_schema import BaseResponse

class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Optionally log the full traceback for debugging
            traceback.print_exc()

            base_response = BaseResponse[str](
                statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="An unexpected error occurred.",
                data=str(e)
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=base_response.dict()
            )
