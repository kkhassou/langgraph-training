"""
RAG Query Atomic Workflow - RAG検索機能

このワークフローはRAGノードを使用して、
ベクトルデータベースから関連情報を検索し、
LLMで拡張応答を生成します。
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
import logging

from src.nodes.base import NodeState
from src.nodes.primitives.rag.simple.node import RAGNode

logger = logging.getLogger(__name__)


class RAGQueryInput(BaseModel):
    """RAG Query workflow input"""
    query: str = Field(..., description="User query")
    collection_name: str = Field(default="default_collection", description="Vector store collection name")
    top_k: int = Field(default=5, description="Number of documents to retrieve")


class RAGQueryOutput(BaseModel):
    """RAG Query workflow output"""
    answer: str = Field(..., description="Generated answer")
    retrieved_documents: List[Dict[str, Any]] = Field(default_factory=list, description="Retrieved documents")
    success: bool = Field(default=True, description="Success flag")
    error_message: str = Field(default="", description="Error message if any")


class RAGQueryWorkflow:
    """RAG検索ワークフロー
    
    RAGNodeを使用して、ベクトルデータベースから関連情報を検索し、
    LLMで質問に答えます。
    """

    def __init__(self):
        self.rag_node = RAGNode()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraphを構築"""
        workflow = StateGraph(NodeState)

        # ノードを追加
        workflow.add_node("rag", self.rag_node.execute)

        # フローを定義
        workflow.add_edge(START, "rag")
        workflow.add_edge("rag", END)

        return workflow.compile()

    async def run(self, input_data: RAGQueryInput) -> RAGQueryOutput:
        """ワークフローを実行
        
        Args:
            input_data: RAGクエリ入力
            
        Returns:
            RAGQueryOutput: 生成された回答と検索されたドキュメント
        """
        try:
            # 状態を作成
            state = NodeState()
            state.data["query"] = input_data.query
            state.data["collection_name"] = input_data.collection_name
            state.data["top_k"] = input_data.top_k

            # グラフを実行
            logger.info(f"Executing RAG workflow with query: {input_data.query[:50]}...")
            result_state = await self.graph.ainvoke(state)

            # エラーチェック
            if "error" in result_state.data:
                return RAGQueryOutput(
                    answer="",
                    retrieved_documents=[],
                    success=False,
                    error_message=result_state.data["error"]
                )

            # 結果を返す
            answer = result_state.data.get("rag_answer", "")
            documents = result_state.data.get("retrieved_documents", [])
            logger.info(f"RAG workflow completed: {len(documents)} documents retrieved")

            return RAGQueryOutput(
                answer=answer,
                retrieved_documents=documents,
                success=True
            )

        except Exception as e:
            logger.error(f"Error in RAG workflow: {e}")
            return RAGQueryOutput(
                answer="",
                retrieved_documents=[],
                success=False,
                error_message=str(e)
            )

