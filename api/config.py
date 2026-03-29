import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_client_id: str = ""
    google_client_secret: str = ""
    oauth_redirect_uri: str = "http://localhost:8080/auth/gmail/callback"
    app_secret_key: str = "change-this-before-deploying"
    app_env: str = "development"
    app_port: int = 8080
    gemini_api_key: str = ""
    database_url: str = "sqlite:///./second_brain.db"
    unkey_root_key: str = ""
    unkey_api_id: str = ""

    class Config:
        env_file = ".env"


settings = Settings()

# Google ADK reads GOOGLE_API_KEY env var for Gemini
if settings.gemini_api_key:
    os.environ["GOOGLE_API_KEY"] = settings.gemini_api_key
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"
