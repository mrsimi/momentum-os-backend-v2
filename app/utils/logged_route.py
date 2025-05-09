from fastapi import Request, Response, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from http.client import responses
from json import JSONDecodeError
from starlette.exceptions import HTTPException as StarletteHTTPException
from traceback import format_exc
from typing import Callable
import logging

# Python builtin logging
logging.basicConfig(
    format="%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
    level=logging.INFO
)

# FastAPI custom logging
class LoggedRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        sensitives_payload = ['password']

        async def custom_route_handler(request: Request) -> Response:
            request_params = ""

            try:
                # Decode request JSON body
                request_json = await request.json()
                request_params += " ".join(f"{k}={v}" for k, v in request_json.items() if k.lower() not in sensitives_payload)
            except JSONDecodeError:
                # Request has no JSON body
                pass

            # Decode request query params
            if request.query_params:
                request_params += " " if request_params else "" # add space for pretty printing
                request_params += " ".join(f"{k}={v}" for k, v in request.query_params.items() if k.lower() not in sensitives_payload)

            # Log the request
            route_called = f"{request.method} {request.url.path} ({request_params})"
            request_log = f"Request from {request.client.host}:{request.client.port}: {route_called}"
            response_log = f"Response to {request.client.host}:{request.client.port}: {route_called}"
            logging.info(request_log)

            # Log the response
            try:
                response: Response = await original_route_handler(request)

                # Successful response
                success_info = f"{response.status_code} {responses[response.status_code]}"
                logging.info(f"{response_log} - {success_info}")
                return response
            except (HTTPException, StarletteHTTPException) as exc:
                # HTTP exception
                error_info = f"{exc.status_code} {responses[exc.status_code]}: {exc.detail}"
                logging.info(f"{response_log} - {error_info}")
                raise exc
            except RequestValidationError as exc:
                # Validation error
                error_info = f"422 {responses[422]}: {exc.__class__.__name__}"
                logging.info(f"{response_log} - {error_info}")
                raise exc
            except Exception as exc:
                # Any other error
                error_info = f"500 {responses[500]}: {exc.__class__.__name__}"
                error_trace = format_exc()
                logging.info(f"{response_log} - {error_info}\n{error_trace}")
                raise HTTPException(500, error_trace)

        return custom_route_handler