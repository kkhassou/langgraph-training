from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class BaseEmbeddingProvider(ABC):
    """Base class for embedding providers"""

    def __init__(self, model_name: str, dimension: int = 768):
        self.model_name = model_name
        self.dimension = dimension

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        pass

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a query (may use different processing)"""
        pass

    def get_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            "provider": self.__class__.__name__,
            "model_name": self.model_name,
            "dimension": self.dimension
        }