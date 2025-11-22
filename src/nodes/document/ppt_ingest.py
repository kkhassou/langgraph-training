"""PowerPoint Ingest Node - PPTファイルからテキスト抽出"""

import os
from typing import List, Dict, Any

from src.nodes.base import BaseNode, NodeState, NodeInput, NodeOutput
from src.services.document.document_service import DocumentService


class PowerPointIngestNode(BaseNode):
    """Node for ingesting and extracting text from PowerPoint files
    
    シンプルなOrchestrationのみ - 実際の処理はDocumentServiceに委譲
    """

    def __init__(self):
        super().__init__(
            name="ppt_ingest",
            description="Extract text content from PowerPoint presentations"
        )
        self.document_service = DocumentService()

    async def execute(self, state: NodeState) -> NodeState:
        """Execute PowerPoint text extraction - サービスに委譲"""
        try:
            file_path = state.data.get("file_path")
            if not file_path:
                raise ValueError("file_path is required in state.data")

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"PowerPoint file not found: {file_path}")

            # ✅ DocumentServiceに処理を委譲（たった1行！）
            slides = await self.document_service.extract_from_ppt(file_path)

            # スライドをDict形式に変換
            extracted_text = [slide.dict() for slide in slides]

            # Update state
            state.data["extracted_text"] = extracted_text
            state.data["slide_count"] = len(extracted_text)
            state.messages.append(f"Extracted text from {len(extracted_text)} slides")
            state.metadata["node"] = self.name

            return state

        except Exception as e:
            state.data["error"] = str(e)
            state.metadata["error_node"] = self.name
            return state


class PPTIngestInput(NodeInput):
    """Input model for PowerPoint ingest node"""
    file_path: str


class PPTIngestOutput(NodeOutput):
    """Output model for PowerPoint ingest node"""
    slide_count: int = 0
    extracted_slides: List[Dict[str, Any]] = []


async def ppt_ingest_handler(file_path: str) -> PPTIngestOutput:
    """Standalone handler for PowerPoint ingest API endpoint"""
    try:
        node = PowerPointIngestNode()
        state = NodeState()
        state.data["file_path"] = file_path

        result_state = await node.execute(state)

        if "error" in result_state.data:
            return PPTIngestOutput(
                output_text="",
                success=False,
                error_message=result_state.data["error"]
            )

        extracted_text = result_state.data.get("extracted_text", [])

        # Format output text using service
        output_text = DocumentService.format_slides_as_text(
            [DocumentService.SlideContent(**slide) for slide in extracted_text]
        )

        return PPTIngestOutput(
            output_text=output_text,
            slide_count=result_state.data.get("slide_count", 0),
            extracted_slides=extracted_text,
            data=result_state.data
        )

    except Exception as e:
        return PPTIngestOutput(
            output_text="",
            success=False,
            error_message=str(e)
        )
