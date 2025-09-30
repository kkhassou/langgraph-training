from typing import List, Dict, Any
from app.infrastructure.search.base import BaseSearchProvider, SearchQuery, SearchResult
from app.infrastructure.vector_stores.base import Document
from app.infrastructure.embeddings.gemini import GeminiEmbeddingProvider
from app.core.config import settings


class SemanticSearchProvider(BaseSearchProvider):
    """Semantic search using embeddings"""

    def __init__(self, name: str = "semantic"):
        super().__init__(name)
        self.embedding_provider = None
        self.documents = []

    def _initialize_embedding_provider(self):
        """Initialize embedding provider lazily"""
        if self.embedding_provider is None:
            self.embedding_provider = GeminiEmbeddingProvider(
                model_name=settings.gemini_embedding_model,
                dimension=settings.embedding_dimension
            )

    async def build_index(self, documents: List[Document]) -> bool:
        """Build semantic index (generate embeddings for documents)"""
        try:
            self._initialize_embedding_provider()
            self.documents = documents

            # Generate embeddings for documents that don't have them
            for doc in documents:
                if doc.embedding is None:
                    doc.embedding = await self.embedding_provider.embed_text(doc.content)

            return True

        except Exception as e:
            print(f"Error building semantic index: {str(e)}")
            return False

    async def search(self, query: SearchQuery, documents: List[Document] = None) -> List[SearchResult]:
        """Perform semantic search using cosine similarity"""
        try:
            self._initialize_embedding_provider()

            # Use provided documents or fall back to indexed documents
            search_documents = documents if documents else self.documents
            if not search_documents:
                return []

            # Ensure documents have embeddings
            await self.build_index(search_documents)

            # Generate query embedding
            query_embedding = await self.embedding_provider.embed_query(query.text)

            # Calculate similarities and create results
            results = []
            for i, doc in enumerate(search_documents):
                # Apply filters if specified
                if query.filters:
                    if not self._matches_filters(doc, query.filters):
                        continue

                if doc.embedding:
                    similarity = self._cosine_similarity(query_embedding, doc.embedding)

                    if similarity >= settings.similarity_threshold:
                        result = SearchResult(
                            document=doc,
                            score=similarity,
                            search_type="semantic",
                            rank=i
                        )
                        results.append(result)

            # Sort by similarity (descending) and return top_k
            results.sort(key=lambda x: x.score, reverse=True)

            # Update ranks after sorting
            for i, result in enumerate(results[:query.top_k]):
                result.rank = i

            return results[:query.top_k]

        except Exception as e:
            print(f"Error in semantic search: {str(e)}")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        import math

        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _matches_filters(self, document: Document, filters: Dict[str, Any]) -> bool:
        """Check if document matches the given filters"""
        for key, value in filters.items():
            if key not in document.metadata:
                return False
            if document.metadata[key] != value:
                return False
        return True

    def get_info(self) -> Dict[str, Any]:
        """Get semantic search provider information"""
        info = super().get_info()
        info.update({
            "algorithm": "Cosine Similarity",
            "type": "semantic_search",
            "embedding_model": settings.gemini_embedding_model,
            "embedding_dimension": settings.embedding_dimension,
            "indexed_documents": len(self.documents) if self.documents else 0,
            "similarity_threshold": settings.similarity_threshold,
            "supports_filters": True
        })
        return info