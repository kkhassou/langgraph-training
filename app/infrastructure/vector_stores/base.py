from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Document:
    """Document representation for vector storage"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """Search result from vector store"""
    document: Document
    score: float
    rank: int


class BaseVectorStore(ABC):
    """Base class for vector stores"""

    def __init__(self, dimension: int = 768):
        self.dimension = dimension

    @abstractmethod
    async def create_collection(self, collection_name: str) -> bool:
        """Create a new collection"""
        pass

    @abstractmethod
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection"""
        pass

    @abstractmethod
    async def add_documents(
        self,
        collection_name: str,
        documents: List[Document]
    ) -> bool:
        """Add documents to collection"""
        pass

    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar documents"""
        pass

    @abstractmethod
    async def delete_documents(
        self,
        collection_name: str,
        document_ids: List[str]
    ) -> bool:
        """Delete documents by IDs"""
        pass

    @abstractmethod
    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get collection information"""
        pass

    def get_info(self) -> Dict[str, Any]:
        """Get vector store information"""
        return {
            "provider": self.__class__.__name__,
            "dimension": self.dimension
        }