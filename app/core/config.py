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

        # RAG Configuration
        self.embedding_model: str = os.getenv("EMBEDDING_MODEL", "gemini")
        self.embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "768"))
        self.gemini_embedding_model: str = os.getenv("GEMINI_EMBEDDING_MODEL", "models/embedding-001")

        # Supabase Configuration
        self.supabase_url: Optional[str] = os.getenv("SUPABASE_URL")
        self.supabase_key: Optional[str] = os.getenv("SUPABASE_KEY")
        self.supabase_service_key: Optional[str] = os.getenv("SUPABASE_SERVICE_KEY")

        # Document Processing
        self.max_chunk_size: int = int(os.getenv("MAX_CHUNK_SIZE", "1000"))
        self.chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "200"))

        # Search & Retrieval
        self.similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))
        self.max_retrieval_results: int = int(os.getenv("MAX_RETRIEVAL_RESULTS", "5"))


settings = Settings()