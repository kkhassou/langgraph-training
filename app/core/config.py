from typing import Optional
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings:
    """Simple settings class for environment configuration"""

    def __init__(self):
        self.app_name: str = "LangGraph Training"
        self.debug: bool = True

        # API Keys
        self.gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
        self.slack_token: Optional[str] = os.getenv("SLACK_TOKEN")

        # Jira Configuration
        self.jira_token: Optional[str] = os.getenv("JIRA_TOKEN")
        self.jira_server: Optional[str] = os.getenv("JIRA_SERVER")
        self.jira_email: Optional[str] = os.getenv("JIRA_EMAIL")


settings = Settings()