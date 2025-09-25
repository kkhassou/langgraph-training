from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "LangGraph Training"
    debug: bool = True

    # API Keys
    gemini_api_key: Optional[str] = None
    slack_token: Optional[str] = None

    # Jira Configuration
    jira_token: Optional[str] = None
    jira_server: Optional[str] = None
    jira_email: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()