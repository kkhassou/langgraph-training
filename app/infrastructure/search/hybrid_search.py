from typing import List, Dict, Any, Optional
from app.infrastructure.search.base import BaseSearchProvider, SearchQuery, SearchResult
from app.infrastructure.search.semantic_search import SemanticSearchProvider
from app.infrastructure.search.bm25_search import BM25SearchProvider
from app.infrastructure.vector_stores.base import Document


class HybridSearchProvider(BaseSearchProvider):
    """Hybrid search combining semantic and BM25 search"""

    def __init__(self,
                 name: str = "hybrid",
                 semantic_weight: float = 0.7,
                 bm25_weight: float = 0.3):
        super().__init__(name)
        self.semantic_provider = SemanticSearchProvider()
        self.bm25_provider = BM25SearchProvider()
        self.semantic_weight = semantic_weight
        self.bm25_weight = bm25_weight

    async def build_index(self, documents: List[Document]) -> bool:
        """Build both semantic and BM25 indices"""
        try:
            semantic_success = await self.semantic_provider.build_index(documents)
            bm25_success = await self.bm25_provider.build_index(documents)

            return semantic_success and bm25_success

        except Exception as e:
            print(f"Error building hybrid index: {str(e)}")
            return False

    async def search(self, query: SearchQuery, documents: List[Document] = None) -> List[SearchResult]:
        """Perform hybrid search combining semantic and BM25 results"""
        try:
            # Perform both types of search
            semantic_results = await self.semantic_provider.search(query, documents)
            bm25_results = await self.bm25_provider.search(query, documents)

            # Combine and re-rank results
            combined_results = self._combine_results(
                semantic_results,
                bm25_results,
                query.top_k
            )

            return combined_results

        except Exception as e:
            print(f"Error in hybrid search: {str(e)}")
            return []

    def _combine_results(self,
                        semantic_results: List[SearchResult],
                        bm25_results: List[SearchResult],
                        top_k: int) -> List[SearchResult]:
        """Combine and re-rank semantic and BM25 results"""

        # Create a dictionary to aggregate scores by document ID
        document_scores = {}

        # Normalize and add semantic scores
        semantic_scores = [r.score for r in semantic_results]
        if semantic_scores:
            max_semantic = max(semantic_scores) if semantic_scores else 1.0
            min_semantic = min(semantic_scores) if semantic_scores else 0.0
            semantic_range = max_semantic - min_semantic if max_semantic > min_semantic else 1.0

            for result in semantic_results:
                doc_id = result.document.id
                normalized_score = (result.score - min_semantic) / semantic_range
                weighted_score = normalized_score * self.semantic_weight

                if doc_id not in document_scores:
                    document_scores[doc_id] = {
                        'document': result.document,
                        'semantic_score': result.score,
                        'bm25_score': 0.0,
                        'combined_score': weighted_score,
                        'semantic_rank': result.rank,
                        'bm25_rank': None
                    }
                else:
                    document_scores[doc_id]['semantic_score'] = result.score
                    document_scores[doc_id]['semantic_rank'] = result.rank
                    document_scores[doc_id]['combined_score'] += weighted_score

        # Normalize and add BM25 scores
        bm25_scores = [r.score for r in bm25_results]
        if bm25_scores:
            max_bm25 = max(bm25_scores) if bm25_scores else 1.0
            min_bm25 = min(bm25_scores) if bm25_scores else 0.0
            bm25_range = max_bm25 - min_bm25 if max_bm25 > min_bm25 else 1.0

            for result in bm25_results:
                doc_id = result.document.id
                normalized_score = (result.score - min_bm25) / bm25_range
                weighted_score = normalized_score * self.bm25_weight

                if doc_id not in document_scores:
                    document_scores[doc_id] = {
                        'document': result.document,
                        'semantic_score': 0.0,
                        'bm25_score': result.score,
                        'combined_score': weighted_score,
                        'semantic_rank': None,
                        'bm25_rank': result.rank
                    }
                else:
                    document_scores[doc_id]['bm25_score'] = result.score
                    document_scores[doc_id]['bm25_rank'] = result.rank
                    document_scores[doc_id]['combined_score'] += weighted_score

        # Convert to SearchResult objects and sort
        combined_results = []
        for doc_id, scores in document_scores.items():
            result = SearchResult(
                document=scores['document'],
                score=scores['combined_score'],
                search_type="hybrid",
                rank=0  # Will be updated after sorting
            )

            # Add additional metadata about the hybrid score components
            result.document.metadata = result.document.metadata.copy()
            result.document.metadata.update({
                'hybrid_semantic_score': scores['semantic_score'],
                'hybrid_bm25_score': scores['bm25_score'],
                'hybrid_semantic_rank': scores['semantic_rank'],
                'hybrid_bm25_rank': scores['bm25_rank'],
                'hybrid_semantic_weight': self.semantic_weight,
                'hybrid_bm25_weight': self.bm25_weight
            })

            combined_results.append(result)

        # Sort by combined score (descending)
        combined_results.sort(key=lambda x: x.score, reverse=True)

        # Update ranks and return top_k
        for i, result in enumerate(combined_results[:top_k]):
            result.rank = i

        return combined_results[:top_k]

    def set_weights(self, semantic_weight: float, bm25_weight: float):
        """Update the weights for semantic and BM25 components"""
        total = semantic_weight + bm25_weight
        if total > 0:
            self.semantic_weight = semantic_weight / total
            self.bm25_weight = bm25_weight / total
        else:
            self.semantic_weight = 0.7
            self.bm25_weight = 0.3

    def get_info(self) -> Dict[str, Any]:
        """Get hybrid search provider information"""
        info = super().get_info()
        info.update({
            "algorithm": "Hybrid (Semantic + BM25)",
            "type": "hybrid_search",
            "semantic_weight": self.semantic_weight,
            "bm25_weight": self.bm25_weight,
            "semantic_provider": self.semantic_provider.get_info(),
            "bm25_provider": self.bm25_provider.get_info(),
            "supports_filters": True
        })
        return info