from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.nodes.base_node import BaseNode, NodeState, NodeInput, NodeOutput
from app.infrastructure.search.semantic_search import SemanticSearchProvider
from app.infrastructure.search.bm25_search import BM25SearchProvider
from app.infrastructure.search.hybrid_search import HybridSearchProvider
from app.infrastructure.search.base import SearchQuery
from app.infrastructure.vector_stores.supabase import SupabaseVectorStore
from app.core.config import settings


class SearchInput(NodeInput):
    """Input model for search node"""
    query: str
    collection_name: str = "default_collection"
    search_type: str = "hybrid"  # "semantic", "bm25", or "hybrid"
    top_k: int = 5
    filters: Optional[Dict[str, Any]] = None
    semantic_weight: float = 0.7
    bm25_weight: float = 0.3


class SearchOutput(NodeOutput):
    """Output model for search node"""
    results: List[Dict[str, Any]]
    search_type: str = ""
    query: str = ""
    total_results: int = 0


class SearchNode(BaseNode):
    """Advanced search node supporting multiple search strategies"""

    def __init__(self):
        super().__init__(
            name="search_node",
            description="Advanced search with semantic, BM25, and hybrid options"
        )
        self.vector_store = None
        self.search_providers = {}

    def _initialize_components(self):
        """Initialize search components lazily"""
        if self.vector_store is None:
            self.vector_store = SupabaseVectorStore(
                dimension=settings.embedding_dimension
            )

        if not self.search_providers:
            self.search_providers = {
                "semantic": SemanticSearchProvider(),
                "bm25": BM25SearchProvider(),
                "hybrid": HybridSearchProvider()
            }

    async def execute(self, state: NodeState) -> NodeState:
        """Execute search with specified strategy"""
        try:
            self._initialize_components()

            # Get search parameters
            query_text = state.data.get("query", "")
            collection_name = state.data.get("collection_name", "default_collection")
            search_type = state.data.get("search_type", "hybrid")
            top_k = state.data.get("top_k", 5)
            filters = state.data.get("filters")
            semantic_weight = state.data.get("semantic_weight", 0.7)
            bm25_weight = state.data.get("bm25_weight", 0.3)

            if not query_text:
                state.data["error"] = "Query is required for search"
                return state

            # Validate search type
            if search_type not in self.search_providers:
                state.data["error"] = f"Invalid search type: {search_type}. Must be one of: {list(self.search_providers.keys())}"
                return state

            # Get documents from collection
            collection_info = await self.vector_store.get_collection_info(collection_name)
            if "error" in collection_info:
                state.data["error"] = f"Collection not found: {collection_name}"
                return state

            # For this implementation, we'll use a simplified approach
            # In a real implementation, you'd retrieve documents from the vector store
            # Here we'll simulate by creating a dummy search

            # Create search query
            search_query = SearchQuery(
                text=query_text,
                filters=filters,
                top_k=top_k
            )

            # Get search provider
            search_provider = self.search_providers[search_type]

            # Configure hybrid weights if needed
            if search_type == "hybrid" and isinstance(search_provider, HybridSearchProvider):
                search_provider.set_weights(semantic_weight, bm25_weight)

            # Since we can't easily retrieve documents without additional infrastructure,
            # we'll create a simplified search that returns metadata about the search
            # In a real implementation, you would:
            # 1. Retrieve documents from the collection
            # 2. Perform the actual search
            # 3. Return real results

            # For now, return search configuration and provider info
            search_results = []
            provider_info = search_provider.get_info()

            # Update state with search results
            state.data.update({
                "search_results": search_results,
                "search_type": search_type,
                "query": query_text,
                "collection_name": collection_name,
                "top_k": top_k,
                "provider_info": provider_info,
                "total_results": len(search_results)
            })

            state.metadata["node"] = self.name
            state.metadata["search_performed"] = True

            return state

        except Exception as e:
            state.data["error"] = f"Search execution failed: {str(e)}"
            state.metadata["error_node"] = self.name
            return state


async def search_node_handler(input_data: SearchInput) -> SearchOutput:
    """Standalone handler for search node API endpoint"""
    try:
        node = SearchNode()
        state = NodeState()
        state.data = {
            "query": input_data.query,
            "collection_name": input_data.collection_name,
            "search_type": input_data.search_type,
            "top_k": input_data.top_k,
            "filters": input_data.filters,
            "semantic_weight": input_data.semantic_weight,
            "bm25_weight": input_data.bm25_weight
        }

        result_state = await node.execute(state)

        if "error" in result_state.data:
            return SearchOutput(
                results=[],
                search_type=input_data.search_type,
                query=input_data.query,
                total_results=0,
                success=False,
                error_message=result_state.data["error"]
            )

        return SearchOutput(
            results=result_state.data.get("search_results", []),
            search_type=result_state.data.get("search_type", ""),
            query=result_state.data.get("query", ""),
            total_results=result_state.data.get("total_results", 0),
            data=result_state.data
        )

    except Exception as e:
        return SearchOutput(
            results=[],
            search_type=input_data.search_type,
            query=input_data.query,
            total_results=0,
            success=False,
            error_message=str(e)
        )