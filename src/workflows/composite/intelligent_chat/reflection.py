"""
Reflection Composite Workflow - 自己批判的推論

このワークフローはChatWorkflowを複数回呼び出して、
生成した回答を自己批判し、改善します。
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
import logging

from src.workflows.atomic.chat import ChatWorkflow, ChatInput

logger = logging.getLogger(__name__)


class ReflectionInput(BaseModel):
    """Reflection workflow input"""
    question: str = Field(..., description="Question to answer")
    reflection_rounds: int = Field(default=2, description="Number of reflection rounds")


class ReflectionOutput(BaseModel):
    """Reflection workflow output"""
    final_answer: str = Field(..., description="Final refined answer")
    iterations: List[Dict[str, str]] = Field(default_factory=list, description="Answer and reflection pairs")
    success: bool = Field(default=True, description="Success flag")
    error_message: str = Field(default="", description="Error message if any")


class ReflectionWorkflow:
    """Reflection（自己批判的推論）ワークフロー
    
    ChatWorkflow（Atomic）を複数回呼び出して、
    回答を生成→批判→改善のサイクルを繰り返します：
    
    1. 初期回答生成（Atomicを使う）
    2. 自己批判（Atomicを使う）
    3. 改善された回答（Atomicを使う）
    4. 必要に応じて繰り返し
    """

    def __init__(self):
        self.chat = ChatWorkflow()

    async def run(self, input_data: ReflectionInput) -> ReflectionOutput:
        """ワークフローを実行
        
        Args:
            input_data: Reflection入力
            
        Returns:
            ReflectionOutput: 改善された回答
        """
        try:
            logger.info(f"Starting Reflection workflow: {input_data.question[:50]}...")

            iterations = []
            current_answer = ""

            # 初期回答を生成
            initial_prompt = f"""以下の質問に答えてください。

質問: {input_data.question}

回答:"""

            initial_result = await self.chat.run(
                ChatInput(message=initial_prompt, temperature=0.7)
            )

            if not initial_result.success:
                return ReflectionOutput(
                    final_answer="",
                    iterations=[],
                    success=False,
                    error_message=f"Initial answer generation failed: {initial_result.error_message}"
                )

            current_answer = initial_result.response
            iterations.append({
                "round": "初期回答",
                "answer": current_answer,
                "reflection": ""
            })

            # Reflectionサイクル
            for round_num in range(1, input_data.reflection_rounds + 1):
                # 自己批判
                critique_prompt = f"""以下の質問と回答を評価し、改善点を指摘してください。

質問: {input_data.question}

現在の回答:
{current_answer}

批判と改善点:"""

                critique_result = await self.chat.run(
                    ChatInput(message=critique_prompt, temperature=0.7)
                )

                if not critique_result.success:
                    logger.warning(f"Reflection round {round_num} critique failed, continuing...")
                    continue

                # 改善された回答を生成
                improve_prompt = f"""以下の批判を踏まえて、回答を改善してください。

質問: {input_data.question}

元の回答:
{current_answer}

批判:
{critique_result.response}

改善された回答:"""

                improve_result = await self.chat.run(
                    ChatInput(message=improve_prompt, temperature=0.7)
                )

                if not improve_result.success:
                    logger.warning(f"Reflection round {round_num} improvement failed, continuing...")
                    continue

                current_answer = improve_result.response
                iterations.append({
                    "round": f"反省サイクル {round_num}",
                    "reflection": critique_result.response,
                    "answer": current_answer
                })

            logger.info(f"Reflection completed with {len(iterations)} iterations")

            return ReflectionOutput(
                final_answer=current_answer,
                iterations=iterations,
                success=True
            )

        except Exception as e:
            logger.error(f"Error in Reflection workflow: {e}")
            return ReflectionOutput(
                final_answer="",
                iterations=[],
                success=False,
                error_message=str(e)
            )


