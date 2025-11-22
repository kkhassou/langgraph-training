"""Retrieval Node - ナレッジベース検索ノード

Difyの「Knowledge Retrieval」ブロックに相当します。
クエリに関連する情報をナレッジベースから検索します。
"""

from typing import Dict, Any, List, Optional
import logging

from src.nodes.base import BaseNode, NodeState, NodeInput, NodeOutput
from src.core.providers.rag import RAGProvider
from src.providers.rag.simple import SimpleRAGProvider

logger = logging.getLogger(__name__)


class RetrievalNode(BaseNode):
    """汎用検索ノード（RAG）
    
    State入力:
        - data["query"]: 検索クエリ（必須）
        - data["collection_name"]: コレクション名（default: "default_collection"）
        - data["top_k"]: 取得件数（default: 5）
    
    State出力:
        - data["rag_answer"]: 生成された回答（もし生成も含むなら）
        - data["retrieved_documents"]: 検索結果リスト
        - data["context_used"]: 使用されたコンテキスト
    """

    def __init__(
        self,
        provider: Optional[RAGProvider] = None,
        name: str = "retrieval_node",
        description: str = "Retrieve relevant documents from knowledge base"
    ):
        super().__init__(name=name, description=description)
        self.provider = provider or SimpleRAGProvider()
        logger.info(f"RetrievalNode initialized with {self.provider.__class__.__name__}")

    async def execute(self, state: NodeState) -> NodeState:
        """検索を実行"""
        try:
            query = state.data.get("query")
            if not query:
                raise ValueError("Query is required for retrieval")

            collection_name = state.data.get("collection_name", "default_collection")
            top_k = state.data.get("top_k", 5)

            logger.info(f"Executing retrieval for query: {query[:50]}...")
            
            # プロバイダーに委譲
            result = await self.provider.query(
                query=query,
                collection_name=collection_name,
                top_k=top_k
            )

            # 結果を格納
            state.data.update({
                "rag_answer": result.answer,
                "retrieved_documents": result.retrieved_documents,
                "context_used": result.context_used
            })

            state.metadata["node"] = self.name
            state.metadata["provider"] = self.provider.__class__.__name__
            state.metadata["documents_retrieved"] = len(result.retrieved_documents)

            return state

        except Exception as e:
            logger.error(f"Error in retrieval node: {e}")
            state.data["error"] = f"Retrieval failed: {str(e)}"
            state.metadata["error_node"] = self.name
            return state


# ✅ 後方互換性のためのエイリアス
class RAGNode(RetrievalNode):
    """RAG Node (deprecated, use RetrievalNode)"""
    pass


class RetrievalInput(NodeInput):
    """Input model for Retrieval node"""
    query: str
    collection_name: str = "default_collection"
    top_k: int = 5


class RetrievalOutput(NodeOutput):
    """Output model for Retrieval node"""
    answer: str
    retrieved_documents: List[Dict[str, Any]]


# ✅ 後方互換性のためのエイリアス
class RAGInput(RetrievalInput):
    """RAG Input (deprecated)"""
    pass

class RAGOutput(RetrievalOutput):
    """RAG Output (deprecated)"""
    pass


async def retrieval_node_handler(input_data: RetrievalInput, provider: Optional[RAGProvider] = None) -> RetrievalOutput:
    """Standalone handler for Retrieval node API endpoint"""
    try:
        node = RetrievalNode(provider=provider)
        state = NodeState()
        state.data = {
            "query": input_data.query,
            "collection_name": input_data.collection_name,
            "top_k": input_data.top_k
        }

        result_state = await node.execute(state)

        if "error" in result_state.data:
            return RetrievalOutput(
                output_text="",
                answer="",
                retrieved_documents=[],
                success=False,
                error_message=result_state.data["error"]
            )

        return RetrievalOutput(
            output_text=result_state.data.get("rag_answer", ""),
            answer=result_state.data.get("rag_answer", ""),
            retrieved_documents=result_state.data.get("retrieved_documents", []),
            data=result_state.data
        )

    except Exception as e:
        return RetrievalOutput(
            output_text="",
            answer="",
            retrieved_documents=[],
            success=False,
            error_message=str(e)
        )
