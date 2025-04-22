from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "FastAPI Boilerplate"
    API_V1_STR: str = "/api/v1"

settings = Settings() 