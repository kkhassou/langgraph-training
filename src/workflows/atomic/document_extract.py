"""
Document Extract Atomic Workflow - ドキュメント抽出機能

このワークフローはPowerPointファイルからテキストを抽出します。
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
import logging

from src.nodes.base import NodeState
from src.nodes.document.ppt_ingest import PowerPointIngestNode

logger = logging.getLogger(__name__)


class DocumentExtractInput(BaseModel):
    """Document Extract workflow input"""
    file_path: str = Field(..., description="Path to the PowerPoint file")


class DocumentExtractOutput(BaseModel):
    """Document Extract workflow output"""
    extracted_text: str = Field(..., description="Extracted text content")
    slide_count: int = Field(..., description="Number of slides")
    slides: List[Dict[str, Any]] = Field(default_factory=list, description="Slide details")
    success: bool = Field(default=True, description="Success flag")
    error_message: str = Field(default="", description="Error message if any")


class DocumentExtractWorkflow:
    """ドキュメント抽出ワークフロー
    
    PowerPointIngestNodeを使用して、PPTファイルからテキストを抽出します。
    """

    def __init__(self):
        self.ppt_node = PowerPointIngestNode()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraphを構築"""
        workflow = StateGraph(NodeState)

        # ノードを追加
        workflow.add_node("ppt_extract", self.ppt_node.execute)

        # フローを定義
        workflow.add_edge(START, "ppt_extract")
        workflow.add_edge("ppt_extract", END)

        return workflow.compile()

    async def run(self, input_data: DocumentExtractInput) -> DocumentExtractOutput:
        """ワークフローを実行
        
        Args:
            input_data: ドキュメント抽出入力
            
        Returns:
            DocumentExtractOutput: 抽出されたテキストとスライド情報
        """
        try:
            # 状態を作成
            state = NodeState()
            state.data["file_path"] = input_data.file_path

            # グラフを実行
            logger.info(f"Executing document extract workflow: {input_data.file_path}")
            result_state = await self.graph.ainvoke(state)

            # エラーチェック
            if "error" in result_state.data:
                return DocumentExtractOutput(
                    extracted_text="",
                    slide_count=0,
                    slides=[],
                    success=False,
                    error_message=result_state.data["error"]
                )

            # 結果を返す
            slides = result_state.data.get("extracted_text", [])
            slide_count = result_state.data.get("slide_count", 0)
            
            # テキストを結合
            text_parts = []
            for slide in slides:
                text_parts.append(f"[Slide {slide.get('slide_number', 0)}]")
                if slide.get('title'):
                    text_parts.append(f"Title: {slide['title']}")
                if slide.get('content'):
                    text_parts.append(f"Content: {slide['content']}")
                text_parts.append("")  # 空行
            
            extracted_text = "\n".join(text_parts)
            logger.info(f"Document extract completed: {slide_count} slides")

            return DocumentExtractOutput(
                extracted_text=extracted_text,
                slide_count=slide_count,
                slides=slides,
                success=True
            )

        except Exception as e:
            logger.error(f"Error in document extract workflow: {e}")
            return DocumentExtractOutput(
                extracted_text="",
                slide_count=0,
                slides=[],
                success=False,
                error_message=str(e)
            )

