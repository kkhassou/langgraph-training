"""
PPT Summary Composite Workflow - PowerPoint要約

このワークフローは2つのAtomicワークフローを組み合わせます：
1. DocumentExtractWorkflow - PPTからテキスト抽出
2. ChatWorkflow - LLMで要約生成
"""

from typing import Dict, Any
from pydantic import BaseModel, Field
import logging

from src.workflows.atomic.document_extract import DocumentExtractWorkflow, DocumentExtractInput
from src.workflows.atomic.chat import ChatWorkflow, ChatInput

logger = logging.getLogger(__name__)


class PPTSummaryInput(BaseModel):
    """PPT Summary workflow input"""
    file_path: str = Field(..., description="Path to the PowerPoint file")
    summary_style: str = Field(
        default="bullet_points",
        description="Summary style: bullet_points, paragraph, or detailed"
    )


class PPTSummaryOutput(BaseModel):
    """PPT Summary workflow output"""
    summary: str = Field(..., description="Generated summary")
    slide_count: int = Field(..., description="Number of slides processed")
    success: bool = Field(default=True, description="Success flag")
    error_message: str = Field(default="", description="Error message if any")


class PPTSummaryWorkflow:
    """PowerPoint要約ワークフロー
    
    2つのAtomicワークフローを組み合わせて、
    PPTファイルの内容を要約します：
    
    1. DocumentExtract（Atomic）でテキスト抽出
    2. Chat（Atomic）で要約生成
    """

    def __init__(self):
        self.extractor = DocumentExtractWorkflow()
        self.chat = ChatWorkflow()

    async def run(self, input_data: PPTSummaryInput) -> PPTSummaryOutput:
        """ワークフローを実行
        
        Args:
            input_data: PPT要約入力
            
        Returns:
            PPTSummaryOutput: 生成された要約
        """
        try:
            logger.info(f"Starting PPT summary workflow: {input_data.file_path}")

            # Step 1: Extract text from PPT（Atomicを使う）
            extract_result = await self.extractor.run(
                DocumentExtractInput(file_path=input_data.file_path)
            )

            if not extract_result.success:
                return PPTSummaryOutput(
                    summary="",
                    slide_count=0,
                    success=False,
                    error_message=f"Extraction failed: {extract_result.error_message}"
                )

            # Step 2: Generate summary using LLM（Atomicを使う）
            prompt = self._create_summary_prompt(
                extract_result.extracted_text,
                input_data.summary_style
            )

            chat_result = await self.chat.run(
                ChatInput(
                    message=prompt,
                    temperature=0.5,  # 要約には低めの温度
                    max_tokens=2000
                )
            )

            if not chat_result.success:
                return PPTSummaryOutput(
                    summary="",
                    slide_count=extract_result.slide_count,
                    success=False,
                    error_message=f"Summary generation failed: {chat_result.error_message}"
                )

            logger.info(f"PPT summary completed: {extract_result.slide_count} slides")

            return PPTSummaryOutput(
                summary=chat_result.response,
                slide_count=extract_result.slide_count,
                success=True
            )

        except Exception as e:
            logger.error(f"Error in PPT summary workflow: {e}")
            return PPTSummaryOutput(
                summary="",
                slide_count=0,
                success=False,
                error_message=str(e)
            )

    def _create_summary_prompt(self, extracted_text: str, style: str) -> str:
        """要約プロンプトを作成"""
        style_instructions = {
            "bullet_points": "以下のプレゼンテーション内容を、箇条書き形式で要約してください。主要なポイントを3-5個にまとめてください。",
            "paragraph": "以下のプレゼンテーション内容を、段落形式で簡潔に要約してください。全体の流れが分かるようにしてください。",
            "detailed": "以下のプレゼンテーション内容を、詳細に要約してください。各スライドの重要な情報を網羅してください。"
        }

        instruction = style_instructions.get(style, style_instructions["bullet_points"])

        return f"""{instruction}

プレゼンテーション内容:
{extracted_text}

要約:"""


