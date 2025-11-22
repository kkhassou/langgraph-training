"""
Chain of Thought Composite Workflow - 段階的推論

このワークフローはChatWorkflowを複数回呼び出して、
段階的な推論を実現します。
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
import logging

from src.workflows.atomic.chat import ChatWorkflow, ChatInput

logger = logging.getLogger(__name__)


class ChainOfThoughtInput(BaseModel):
    """Chain of Thought workflow input"""
    question: str = Field(..., description="Question to reason about")
    steps: int = Field(default=3, description="Number of reasoning steps")


class ChainOfThoughtOutput(BaseModel):
    """Chain of Thought workflow output"""
    final_answer: str = Field(..., description="Final answer after reasoning")
    reasoning_steps: List[str] = Field(default_factory=list, description="Intermediate reasoning steps")
    success: bool = Field(default=True, description="Success flag")
    error_message: str = Field(default="", description="Error message if any")


class ChainOfThoughtWorkflow:
    """Chain of Thought（段階的推論）ワークフロー
    
    ChatWorkflow（Atomic）を複数回呼び出して、
    段階的に推論を深めていきます：
    
    1. 問題分析（Atomicを使う）
    2. 推論ステップ（Atomicを使う）
    3. 最終回答（Atomicを使う）
    """

    def __init__(self):
        self.chat = ChatWorkflow()

    async def run(self, input_data: ChainOfThoughtInput) -> ChainOfThoughtOutput:
        """ワークフローを実行
        
        Args:
            input_data: CoT入力
            
        Returns:
            ChainOfThoughtOutput: 段階的推論の結果
        """
        try:
            logger.info(f"Starting Chain of Thought workflow: {input_data.question[:50]}...")

            reasoning_steps = []

            # Step 1: 問題を分析
            analysis_prompt = f"""以下の質問を分析してください。どのような情報や推論ステップが必要か考えてください。

質問: {input_data.question}

分析:"""

            analysis_result = await self.chat.run(
                ChatInput(message=analysis_prompt, temperature=0.7)
            )

            if not analysis_result.success:
                return ChainOfThoughtOutput(
                    final_answer="",
                    reasoning_steps=[],
                    success=False,
                    error_message=f"Analysis failed: {analysis_result.error_message}"
                )

            reasoning_steps.append(f"[分析]\n{analysis_result.response}")

            # Step 2: 段階的に推論
            current_context = analysis_result.response

            for step_num in range(1, input_data.steps + 1):
                step_prompt = f"""前のステップの分析に基づいて、次の推論ステップを実行してください。

質問: {input_data.question}

これまでの分析:
{current_context}

ステップ {step_num} の推論:"""

                step_result = await self.chat.run(
                    ChatInput(message=step_prompt, temperature=0.7)
                )

                if not step_result.success:
                    logger.warning(f"Reasoning step {step_num} failed, continuing...")
                    continue

                reasoning_steps.append(f"[ステップ {step_num}]\n{step_result.response}")
                current_context += f"\n\n{step_result.response}"

            # Step 3: 最終回答を生成
            final_prompt = f"""これまでの分析と推論に基づいて、最終的な回答を提供してください。

質問: {input_data.question}

これまでの推論:
{current_context}

最終回答:"""

            final_result = await self.chat.run(
                ChatInput(message=final_prompt, temperature=0.5)
            )

            if not final_result.success:
                return ChainOfThoughtOutput(
                    final_answer="",
                    reasoning_steps=reasoning_steps,
                    success=False,
                    error_message=f"Final answer generation failed: {final_result.error_message}"
                )

            logger.info(f"Chain of Thought completed with {len(reasoning_steps)} steps")

            return ChainOfThoughtOutput(
                final_answer=final_result.response,
                reasoning_steps=reasoning_steps,
                success=True
            )

        except Exception as e:
            logger.error(f"Error in Chain of Thought workflow: {e}")
            return ChainOfThoughtOutput(
                final_answer="",
                reasoning_steps=[],
                success=False,
                error_message=str(e)
            )

