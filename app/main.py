import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from app.api.endpoints import auth_endpoint, checkin_response_endpoint, project_endpoint
from app.services.notify_service import fetch_checkins_and_notify
load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
    level=logging.INFO
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async def runner():
        # Sleep until the top of the next hour
        now = datetime.now(timezone.utc)
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        wait_seconds = (next_hour - now).total_seconds()
        logging.info(f"Sleeping for {int(wait_seconds)}s to align to next hour at {next_hour.isoformat()} UTC")
        await asyncio.sleep(wait_seconds)

        # Then run every hour exactly on the hour
        while True:
            logging.info(f"Running check-in task at {datetime.now(timezone.utc).isoformat()} UTC")
            await fetch_checkins_and_notify()
            await asyncio.sleep(3600)  # wait for the next hour

    task = asyncio.create_task(runner())
    yield
    
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logging.info("Background task cancelled during shutdown.")

app = FastAPI(
    title=os.getenv("PROJECT_NAME"),
    openapi_url=f"{os.getenv('API_V1_STR')}/openapi.json",
    lifespan=lifespan
)



#app.add_middleware(ExceptionHandlerMiddleware)

origins = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [origin.strip() for origin in origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # or ["*"] for testing (not recommended in prod)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
#app.include_router(api_router, prefix=os.getenv("API_V1_STR"))

app.include_router(auth_endpoint.router, prefix=os.getenv("API_V1_STR"))
app.include_router(project_endpoint.router, prefix=os.getenv("API_V1_STR"))
app.include_router(checkin_response_endpoint.router, prefix=os.getenv("API_V1_STR"))

#handler = Mangum(app)

