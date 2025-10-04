from typing import List, Dict, Any
import google.generativeai as genai
from app.infrastructure.embeddings.base import BaseEmbeddingProvider
from app.core.config import settings


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Gemini Embedding API provider"""

    def __init__(self, model_name: str = "models/embedding-001", dimension: int = 768):
        super().__init__(model_name, dimension)
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Gemini client"""
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for embedding generation")

        genai.configure(api_key=settings.gemini_api_key)

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            result = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type="retrieval_document",
                title="Document"
            )
            return result['embedding']
        except Exception as e:
            raise RuntimeError(f"Failed to generate embedding: {str(e)}")

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        embeddings = []
        for text in texts:
            embedding = await self.embed_text(text)
            embeddings.append(embedding)
        return embeddings

    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a query"""
        try:
            result = genai.embed_content(
                model=self.model_name,
                content=query,
                task_type="retrieval_query"
            )
            return result['embedding']
        except Exception as e:
            raise RuntimeError(f"Failed to generate query embedding: {str(e)}")

    def get_info(self) -> Dict[str, Any]:
        """Get provider information"""
        info = super().get_info()
        info.update({
            "api_type": "Gemini Embedding API",
            "supports_batch": False,
            "task_types": ["retrieval_document", "retrieval_query"]
        })
        return info