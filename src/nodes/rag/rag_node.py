"""RAG Node - プロバイダー注入可能なRAGノード（キャッシング対応）"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from src.nodes.base import BaseNode, NodeState, NodeInput, NodeOutput
from src.core.providers.rag import RAGProvider
from src.providers.rag.simple import SimpleRAGProvider
from src.infrastructure.cache.rag_cache import RAGCache, get_global_cache

logger = logging.getLogger(__name__)


class RAGInput(NodeInput):
    """Input model for RAG node"""
    query: str
    collection_name: str = "default_collection"
    top_k: int = 5
    include_metadata: bool = True


class RAGOutput(NodeOutput):
    """Output model for RAG node"""
    answer: str
    retrieved_documents: List[Dict[str, Any]]
    query_embedding: Optional[List[float]] = None
    
    # Ensure output_text is populated for compatibility with NodeOutput
    def __init__(self, **data):
        if 'output_text' not in data and 'answer' in data:
            data['output_text'] = data['answer']
        super().__init__(**data)


class RAGNode(BaseNode):
    """RAG (Retrieval-Augmented Generation) Node（キャッシング対応）
    
    依存性注入パターンを使用し、任意のRAGProviderを注入できます。
    これにより、テスト時のモック化や、異なるRAG実装への切り替えが容易になります。
    
    パフォーマンス最適化機能：
    - RAG検索結果のキャッシング（同じクエリの重複検索を回避）
    - キャッシュヒット率の追跡
    - TTL（Time To Live）による自動キャッシュ無効化
    
    Example:
        >>> from src.providers.rag.simple import SimpleRAGProvider
        >>> provider = SimpleRAGProvider()
        >>> # キャッシング有効
        >>> node = RAGNode(provider=provider, enable_cache=True)
        >>> result = await node.execute(state)
        >>> 
        >>> # キャッシング無効
        >>> node = RAGNode(provider=provider, enable_cache=False)
    """

    def __init__(
        self,
        provider: Optional[RAGProvider] = None,
        name: str = "rag_node",
        description: str = "Retrieve relevant documents and generate augmented response",
        enable_cache: bool = True,
        cache: Optional[RAGCache] = None
    ):
        """
        Args:
            provider: RAGプロバイダー実装（省略時はSimpleRAGProvider）
            name: ノード名
            description: ノードの説明
            enable_cache: キャッシングを有効化するか（デフォルト: True）
            cache: カスタムキャッシュインスタンス（省略時はグローバルキャッシュ）
        """
        super().__init__(name=name, description=description)
        # プロバイダーが指定されていない場合はデフォルトを使用
        self.provider = provider or SimpleRAGProvider()
        self.enable_cache = enable_cache
        
        # キャッシュインスタンスを設定
        if enable_cache:
            self.cache = cache or get_global_cache()
            logger.info(
                f"RAGNode initialized with {self.provider.__class__.__name__} "
                f"(cache enabled: {self.cache})"
            )
        else:
            self.cache = None
            logger.info(
                f"RAGNode initialized with {self.provider.__class__.__name__} "
                f"(cache disabled)"
            )

    async def execute(self, state: NodeState) -> NodeState:
        """Execute RAG workflow - プロバイダーに委譲（キャッシング対応）"""
        try:
            # パラメータを取得
            query = state.data.get("query", "")
            collection_name = state.data.get("collection_name", "default_collection")
            top_k = state.data.get("top_k", 5)
            include_metadata = state.data.get("include_metadata", True)

            if not query:
                state.data["error"] = "Query is required for RAG"
                return state

            # キャッシュをチェック（有効な場合）
            cache_hit = False
            if self.enable_cache and self.cache:
                cached_result = self.cache.get(query, collection_name, top_k)
                if cached_result is not None:
                    logger.info(f"Cache HIT for query: '{query[:50]}...'")
                    cache_hit = True
                    
                    # キャッシュから結果を復元
                    state.data.update({
                        "rag_answer": cached_result[0]["answer"],
                        "retrieved_documents": cached_result[0]["documents"],
                        "query_embedding": cached_result[0].get("embedding"),
                        "context_used": cached_result[0].get("context", "")
                    })
                    
                    state.metadata["node"] = self.name
                    state.metadata["provider"] = self.provider.__class__.__name__
                    state.metadata["documents_retrieved"] = len(cached_result[0]["documents"])
                    state.metadata["cache_hit"] = True
                    
                    return state

            # キャッシュミス: RAGProviderに処理を委譲
            logger.info(
                f"Cache MISS, executing RAG with {self.provider.__class__.__name__}"
            )
            result = await self.provider.query(
                query=query,
                collection_name=collection_name,
                top_k=top_k,
                include_embedding=include_metadata
            )

            # 結果をstateに格納
            state.data.update({
                "rag_answer": result.answer,
                "retrieved_documents": result.retrieved_documents,
                "query_embedding": result.query_embedding,
                "context_used": result.context_used
            })

            state.metadata["node"] = self.name
            state.metadata["provider"] = self.provider.__class__.__name__
            state.metadata["documents_retrieved"] = len(result.retrieved_documents)
            state.metadata["cache_hit"] = False

            # キャッシュに保存（有効な場合）
            if self.enable_cache and self.cache:
                cache_entry = [{
                    "answer": result.answer,
                    "documents": result.retrieved_documents,
                    "embedding": result.query_embedding,
                    "context": result.context_used
                }]
                self.cache.set(query, collection_name, top_k, cache_entry)
                logger.debug(f"Result cached for query: '{query[:50]}...'")

            return state

        except Exception as e:
            logger.error(f"Error in RAG node: {e}")
            state.data["error"] = f"RAG execution failed: {str(e)}"
            state.metadata["error_node"] = self.name
            return state
    
    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """キャッシュ統計情報を取得
        
        Returns:
            キャッシュ有効時は統計情報、無効時はNone
        """
        if self.cache:
            return self.cache.get_stats()
        return None
    
    def clear_cache(self):
        """キャッシュをクリア"""
        if self.cache:
            self.cache.clear()
            logger.info("RAG cache cleared")


async def rag_node_handler(input_data: RAGInput, provider: Optional[RAGProvider] = None) -> RAGOutput:
    """Standalone handler for RAG node API endpoint
    
    Args:
        input_data: 入力データ
        provider: RAGプロバイダー（省略時はSimpleRAGProvider）
    """
    try:
        node = RAGNode(provider=provider)
        state = NodeState()
        state.data = {
            "query": input_data.query,
            "collection_name": input_data.collection_name,
            "top_k": input_data.top_k,
            "include_metadata": input_data.include_metadata
        }

        result_state = await node.execute(state)

        if "error" in result_state.data:
            return RAGOutput(
                answer="",
                retrieved_documents=[],
                output_text="",
                success=False,
                error_message=result_state.data["error"]
            )

        return RAGOutput(
            answer=result_state.data.get("rag_answer", ""),
            retrieved_documents=result_state.data.get("retrieved_documents", []),
            query_embedding=result_state.data.get("query_embedding") if input_data.include_metadata else None,
            output_text=result_state.data.get("rag_answer", ""),
            data=result_state.data
        )

    except Exception as e:
        return RAGOutput(
            answer="",
            retrieved_documents=[],
            output_text="",
            success=False,
            error_message=str(e)
        )
