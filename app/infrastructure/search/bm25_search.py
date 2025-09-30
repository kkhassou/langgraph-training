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
        """Tokenize text for BM25 indexing (supports Japanese)"""
        # Simple tokenization for both English and Japanese
        text = text.lower()
        
        # For Japanese, split into characters and also extract words
        # Remove special characters
        tokens = []
        
        # Extract English words
        english_tokens = re.findall(r'\b[a-z0-9]+\b', text)
        tokens.extend(english_tokens)
        
        # Extract Japanese characters (Hiragana, Katakana, Kanji)
        # Split into character bigrams for better matching
        japanese_chars = re.findall(r'[ぁ-んァ-ヶー一-龯々〆〤]+', text)
        for japanese_word in japanese_chars:
            # Add the whole word
            tokens.append(japanese_word)
            # Add character bigrams for better partial matching
            if len(japanese_word) > 1:
                for i in range(len(japanese_word) - 1):
                    tokens.append(japanese_word[i:i+2])
        
        return tokens if tokens else [text]  # Return original text if no tokens found

    async def build_index(self, documents: List[Document]) -> bool:
        """Build BM25 index from documents"""
        try:
            print(f"[BM25] Building index with {len(documents)} documents...")
            self.documents = documents
            self.tokenized_corpus = []

            for i, doc in enumerate(documents):
                tokens = self._tokenize(doc.content)
                self.tokenized_corpus.append(tokens)
                if i == 0:
                    print(f"[BM25] First document tokenized to {len(tokens)} tokens: {tokens[:10]}...")

            # Build BM25 index
            self.bm25_index = BM25Okapi(self.tokenized_corpus)
            print(f"[BM25] Index built successfully")
            return True

        except Exception as e:
            print(f"[BM25] Error building BM25 index: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    async def search(self, query: SearchQuery, documents: List[Document] = None) -> List[SearchResult]:
        """Perform BM25 search"""
        try:
            # Use provided documents or fall back to indexed documents
            if documents:
                await self.build_index(documents)
            elif self.bm25_index is None:
                print(f"[BM25] No index available for search")
                return []

            # Tokenize query
            query_tokens = self._tokenize(query.text)
            print(f"[BM25] Query '{query.text}' tokenized to {len(query_tokens)} tokens: {query_tokens}")

            # Get BM25 scores
            scores = self.bm25_index.get_scores(query_tokens)
            print(f"[BM25] Got {len(scores)} scores, max score: {max(scores) if len(scores) > 0 else 0}")

            # Create search results
            results = []
            for i, (doc, score) in enumerate(zip(self.documents, scores)):
                # Apply filters if specified
                if query.filters:
                    if not self._matches_filters(doc, query.filters):
                        continue

                # Include all results (even with negative scores)
                # We'll sort and return top_k anyway
                result = SearchResult(
                    document=doc,
                    score=float(score),
                    search_type="bm25",
                    rank=i
                )
                results.append(result)

            print(f"[BM25] Found {len(results)} total results (scores range: {min(scores) if len(scores) > 0 else 0} to {max(scores) if len(scores) > 0 else 0})")

            # Sort by score (descending) and return top_k
            results.sort(key=lambda x: x.score, reverse=True)

            # Update ranks after sorting
            for i, result in enumerate(results[:query.top_k]):
                result.rank = i

            print(f"[BM25] Returning top {min(len(results), query.top_k)} results")
            return results[:query.top_k]

        except Exception as e:
            print(f"[BM25] Error in BM25 search: {str(e)}")
            import traceback
            traceback.print_exc()
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