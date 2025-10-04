from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from src.infrastructure.vector_stores.base import Document


@dataclass
class SearchQuery:
    """Search query representation"""
    text: str
    filters: Optional[Dict[str, Any]] = None
    top_k: int = 5


@dataclass
class SearchResult:
    """Unified search result representation"""
    document: Document
    score: float
    search_type: str  # "semantic", "bm25", or "hybrid"
    rank: int


class BaseSearchProvider(ABC):
    """Base class for search providers"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def search(self, query: SearchQuery, documents: List[Document]) -> List[SearchResult]:
        """Perform search and return ranked results"""
        pass

    @abstractmethod
    async def build_index(self, documents: List[Document]) -> bool:
        """Build search index from documents"""
        pass

    def get_info(self) -> Dict[str, Any]:
        """Get search provider information"""
        return {
            "provider": self.__class__.__name__,
            "name": self.name
        }