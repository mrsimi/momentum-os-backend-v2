import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from app.api.endpoints import auth_endpoint, checkin_response_endpoint, project_endpoint
from app.services.notify_service import fetch_checkins_and_notify
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    async def runner():
        # Sleep until the top of the next hour
        now = datetime.now(timezone.utc)
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        wait_seconds = (next_hour - now).total_seconds()
        print(f"Sleeping for {int(wait_seconds)}s to align to next hour at {next_hour.isoformat()} UTC")
        await asyncio.sleep(wait_seconds)

        # Then run every hour exactly on the hour
        while True:
            print(f"Running check-in task at {datetime.now(timezone.utc).isoformat()} UTC")
            await fetch_checkins_and_notify()
            await asyncio.sleep(3600)  # wait for the next hour

    task = asyncio.create_task(runner())
    yield
    
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("Background task cancelled during shutdown.")

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
#app.include_router(api_router, prefix=os.getenv("API_V1_STR"))

app.include_router(auth_endpoint.router, prefix=os.getenv("API_V1_STR"))
app.include_router(project_endpoint.router, prefix=os.getenv("API_V1_STR"))
app.include_router(checkin_response_endpoint.router, prefix=os.getenv("API_V1_STR"))

