"""RAG Node - プロバイダー注入可能なRAGノード"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from src.nodes.base import BaseNode, NodeState, NodeInput, NodeOutput
from src.core.providers.rag import RAGProvider
from src.providers.rag.simple import SimpleRAGProvider

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
    """RAG (Retrieval-Augmented Generation) Node
    
    依存性注入パターンを使用し、任意のRAGProviderを注入できます。
    これにより、テスト時のモック化や、異なるRAG実装への切り替えが容易になります。
    
    Example:
        >>> from src.providers.rag.simple import SimpleRAGProvider
        >>> provider = SimpleRAGProvider()
        >>> node = RAGNode(provider=provider)
        >>> result = await node.execute(state)
    """

    def __init__(
        self,
        provider: Optional[RAGProvider] = None,
        name: str = "rag_node",
        description: str = "Retrieve relevant documents and generate augmented response"
    ):
        """
        Args:
            provider: RAGプロバイダー実装（省略時はSimpleRAGProvider）
            name: ノード名
            description: ノードの説明
        """
        super().__init__(name=name, description=description)
        # プロバイダーが指定されていない場合はデフォルトを使用
        self.provider = provider or SimpleRAGProvider()
        logger.info(f"RAGNode initialized with {self.provider.__class__.__name__}")

    async def execute(self, state: NodeState) -> NodeState:
        """Execute RAG workflow - プロバイダーに委譲"""
        try:
            # パラメータを取得
            query = state.data.get("query", "")
            collection_name = state.data.get("collection_name", "default_collection")
            top_k = state.data.get("top_k", 5)
            include_metadata = state.data.get("include_metadata", True)

            if not query:
                state.data["error"] = "Query is required for RAG"
                return state

            # ✅ RAGProviderに全ての処理を委譲
            logger.info(f"Executing RAG with {self.provider.__class__.__name__}")
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

            return state

        except Exception as e:
            logger.error(f"Error in RAG node: {e}")
            state.data["error"] = f"RAG execution failed: {str(e)}"
            state.metadata["error_node"] = self.name
            return state


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
