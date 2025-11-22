"""TODO Advisor Node - Generates advice for individual TODO items using LLM"""

from typing import Dict, Any
from pydantic import BaseModel, Field
import logging

from src.nodes.base import BaseNode, NodeResult
from src.services.llm.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class TodoAdvisorInput(BaseModel):
    """Input schema for TODO Advisor node"""
    todo: Dict[str, Any] = Field(..., description="TODO item to advise on")
    index: int = Field(..., description="Index of this TODO in the list")
    total: int = Field(..., description="Total number of TODOs")


class TodoAdvisorNode(BaseNode):
    """Node that generates advice for a single TODO item"""

    def __init__(self):
        super().__init__("todo-advisor")

    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """Generate advice for a TODO item"""
        try:
            todo = input_data.get("todo", {})
            index = input_data.get("index", 0)
            total = input_data.get("total", 1)

            title = todo.get("title", "")
            
            # プロンプト作成（ビジネスロジックに集中）
            prompt = self._create_advice_prompt(todo)
            
            # ✅ GeminiServiceを使ってシンプルに呼び出し
            logger.info(f"Generating advice for TODO {index + 1}/{total}: {title}")
            advice = await GeminiService.generate(
                prompt=prompt,
                temperature=0.7
            )

            result_data = {
                "todo": todo,
                "advice": advice,
                "index": index,
                "total": total
            }

            logger.info(f"Generated advice for TODO {index + 1}/{total}")

            return NodeResult(
                success=True,
                data=result_data,
                metadata={
                    "action": "generate_advice",
                    "index": index,
                    "total": total
                }
            )

        except Exception as e:
            logger.error(f"Error generating advice: {e}")
            return NodeResult(
                success=False,
                error=str(e),
                metadata={"action": "generate_advice"}
            )

    def _create_advice_prompt(self, todo: Dict[str, Any]) -> str:
        """プロンプト作成（ビジネスロジックに集中）"""
        title = todo.get("title", "")
        description = todo.get("description", "")
        priority = todo.get("priority", "medium")
        estimated_time = todo.get("estimated_time", "")

        return f"""
あなたは優秀な生産性コンサルタントです。
以下のタスクについて、実行のためのアドバイスを提供してください。

タスク: {title}
詳細: {description}
優先度: {priority}
予想所要時間: {estimated_time}分

以下の観点でアドバイスしてください（200文字以内）：
1. タスクを効率的に進めるためのコツ
2. 注意すべきポイント
3. 準備しておくべきこと

簡潔で実践的なアドバイスをお願いします。
"""


# Create node instance
todo_advisor_node = TodoAdvisorNode()


async def todo_advisor_handler(input_data: TodoAdvisorInput) -> Dict[str, Any]:
    """Handler function for TODO Advisor node"""
    result = await todo_advisor_node.execute(input_data.model_dump())
    return result.model_dump()
