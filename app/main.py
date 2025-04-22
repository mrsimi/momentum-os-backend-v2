from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
origins = [
    "http://localhost:8080",  # your Vite/React dev server
    "https://momentum-os.vercel.app",  # if your frontend is hosted here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or ["*"] for testing (not recommended in prod)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=os.getenv("API_V1_STR"))
