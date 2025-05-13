from fastapi import Request, Response
from fastapi.routing import APIRoute
from starlette.responses import StreamingResponse
from typing import Callable
import logging
import json

SENSITIVE_KEYS = frozenset({"password", "token", "secret", "access_token", "authorization", "auth", "api_key"})

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def mask_sensitive(data):
    """Recursively mask sensitive fields."""
    if isinstance(data, dict):
        return {
            k: "****" if k.lower() in SENSITIVE_KEYS else mask_sensitive(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [mask_sensitive(item) for item in data]
    return data

class LoggedRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_handler = super().get_route_handler()

        async def custom_handler(request: Request) -> Response:
            # --- Read and log request ---
            body_bytes = await request.body()
            query_params = request.query_params.multi_items()
            request_body_text = body_bytes.decode("utf-8", errors="ignore") if body_bytes else ""

            safe_query_params = {
                k: "****" if k.lower() in SENSITIVE_KEYS else v
                for k, v in query_params
            }

            try:
                parsed = json.loads(request_body_text)
                masked = mask_sensitive(parsed)
                safe_request_body = json.dumps(masked, separators=(",", ":"))
            except Exception:
                safe_request_body = request_body_text

            logging.info(
                f">>> {request.method} {request.url.path} | Query: {safe_query_params} | Body: {safe_request_body}"
            )

            # Rebuild request stream
            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request._receive = receive

            # --- Call original handler ---
            response: Response = await original_handler(request)

            response_body = b""
            if isinstance(response, StreamingResponse):
                chunks = []
                async for chunk in response.body_iterator:
                    chunks.append(chunk)
                    response_body += chunk

                response = Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
            else:
                response_body = getattr(response, "body", b"")

            # --- Log response ---
            try:
                response_text = response_body.decode("utf-8", errors="ignore")
                parsed = json.loads(response_text)
                masked = mask_sensitive(parsed)
                safe_response_body = json.dumps(masked, separators=(",", ":"))
                logging.info(
                    f"<<< {request.method} {request.url.path} | Status: {response.status_code} | JSON: {safe_response_body}"
                )
            except Exception:
                logging.info(
                    f"<<< {request.method} {request.url.path} | Status: {response.status_code} | Raw: {response_body[:500]!r}"
                )

            return response

        return custom_handler
