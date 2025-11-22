"""RAG Node - シンプルな検索拡張生成ノード"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from src.nodes.base import BaseNode, NodeState, NodeInput, NodeOutput
from src.services.rag.rag_service import RAGService


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
    
    シンプルなOrchestrationのみ - 実際の処理はRAGServiceに委譲
    """

    def __init__(self):
        super().__init__(
            name="rag_node",
            description="Retrieve relevant documents and generate augmented response"
        )
        self.rag_service = RAGService()

    async def execute(self, state: NodeState) -> NodeState:
        """Execute RAG workflow - サービスに委譲"""
        try:
            # パラメータを取得
            query = state.data.get("query", "")
            collection_name = state.data.get("collection_name", "default_collection")
            top_k = state.data.get("top_k", 5)
            include_metadata = state.data.get("include_metadata", True)

            if not query:
                state.data["error"] = "Query is required for RAG"
                return state

            # ✅ RAGServiceに全ての処理を委譲（たった1行！）
            result = await self.rag_service.query(
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
            state.metadata["documents_retrieved"] = len(result.retrieved_documents)

            return state

        except Exception as e:
            state.data["error"] = f"RAG execution failed: {str(e)}"
            state.metadata["error_node"] = self.name
            return state


async def rag_node_handler(input_data: RAGInput) -> RAGOutput:
    """Standalone handler for RAG node API endpoint"""
    try:
        node = RAGNode()
        state = NodeState()
        state.data = {
            "query": input_data.query,
            "collection_name": input_data.collection_name,
            "top_k": input_data.top_k
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
