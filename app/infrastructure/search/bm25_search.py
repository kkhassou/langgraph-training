from typing import List, Dict, Any
import re
from rank_bm25 import BM25Okapi
from app.infrastructure.search.base import BaseSearchProvider, SearchQuery, SearchResult
from app.infrastructure.vector_stores.base import Document


class BM25SearchProvider(BaseSearchProvider):
    """BM25 keyword search implementation"""

    def __init__(self, name: str = "bm25"):
        super().__init__(name)
        self.bm25_index = None
        self.documents = []
        self.tokenized_corpus = []

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for BM25 indexing"""
        # Simple tokenization - can be enhanced with proper NLP
        text = text.lower()
        # Remove special characters and split by whitespace
        tokens = re.findall(r'\b\w+\b', text)
        return tokens

    async def build_index(self, documents: List[Document]) -> bool:
        """Build BM25 index from documents"""
        try:
            self.documents = documents
            self.tokenized_corpus = []

            for doc in documents:
                tokens = self._tokenize(doc.content)
                self.tokenized_corpus.append(tokens)

            # Build BM25 index
            self.bm25_index = BM25Okapi(self.tokenized_corpus)
            return True

        except Exception as e:
            print(f"Error building BM25 index: {str(e)}")
            return False

    async def search(self, query: SearchQuery, documents: List[Document] = None) -> List[SearchResult]:
        """Perform BM25 search"""
        try:
            # Use provided documents or fall back to indexed documents
            if documents:
                await self.build_index(documents)
            elif self.bm25_index is None:
                return []

            # Tokenize query
            query_tokens = self._tokenize(query.text)

            # Get BM25 scores
            scores = self.bm25_index.get_scores(query_tokens)

            # Create search results
            results = []
            for i, (doc, score) in enumerate(zip(self.documents, scores)):
                # Apply filters if specified
                if query.filters:
                    if not self._matches_filters(doc, query.filters):
                        continue

                if score > 0:  # Only include documents with positive scores
                    result = SearchResult(
                        document=doc,
                        score=float(score),
                        search_type="bm25",
                        rank=i
                    )
                    results.append(result)

            # Sort by score (descending) and return top_k
            results.sort(key=lambda x: x.score, reverse=True)

            # Update ranks after sorting
            for i, result in enumerate(results[:query.top_k]):
                result.rank = i

            return results[:query.top_k]

        except Exception as e:
            print(f"Error in BM25 search: {str(e)}")
            return []

    def _matches_filters(self, document: Document, filters: Dict[str, Any]) -> bool:
        """Check if document matches the given filters"""
        for key, value in filters.items():
            if key not in document.metadata:
                return False
            if document.metadata[key] != value:
                return False
        return True

    def get_info(self) -> Dict[str, Any]:
        """Get BM25 search provider information"""
        info = super().get_info()
        info.update({
            "algorithm": "BM25 Okapi",
            "type": "keyword_search",
            "indexed_documents": len(self.documents) if self.documents else 0,
            "supports_filters": True
        })
        return info