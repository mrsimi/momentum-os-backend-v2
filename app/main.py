from fastapi import FastAPI

from app.api.api_router import api_router
from dotenv import load_dotenv
import os

from app.middleware import ExceptionHandlerMiddleware
load_dotenv()

app = FastAPI(
    title=os.getenv("PROJECT_NAME"),
    openapi_url=f"{os.getenv('API_V1_STR')}/openapi.json"
)


#app.add_middleware(ExceptionHandlerMiddleware)
app.include_router(api_router, prefix=os.getenv("API_V1_STR"))
