from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_client_id: str
    google_client_secret: str
    oauth_redirect_uri: str = "http://localhost:8080/auth/gmail/callback"
    app_secret_key: str = "change-this-before-deploying"
    app_env: str = "development"
    app_port: int = 8080

    class Config:
        env_file = ".env"


settings = Settings()
