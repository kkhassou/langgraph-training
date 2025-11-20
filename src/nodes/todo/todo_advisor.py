"""TODO Advisor Node - Generates advice for individual TODO items using LLM"""

from typing import Dict, Any
from pydantic import BaseModel, Field
import logging
import os

from src.nodes.base import BaseNode, NodeResult

logger = logging.getLogger(__name__)

# Import Gemini for LLM advice
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google-generativeai not available")


class TodoAdvisorInput(BaseModel):
    """Input schema for TODO Advisor node"""
    todo: Dict[str, Any] = Field(..., description="TODO item to advise on")
    index: int = Field(..., description="Index of this TODO in the list")
    total: int = Field(..., description="Total number of TODOs")


class TodoAdvisorNode(BaseNode):
    """Node that generates advice for a single TODO item"""

    def __init__(self):
        super().__init__("todo-advisor")
        self.api_key = os.getenv("GEMINI_API_KEY")

        if GENAI_AVAILABLE and self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        else:
            self.model = None
            logger.warning("Gemini model not configured")

    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """Generate advice for a TODO item"""
        try:
            todo = input_data.get("todo", {})
            index = input_data.get("index", 0)
            total = input_data.get("total", 1)

            if not self.model:
                raise ValueError("Gemini model not configured. Please set GEMINI_API_KEY")

            title = todo.get("title", "")
            description = todo.get("description", "")
            priority = todo.get("priority", "medium")
            estimated_time = todo.get("estimated_time", "")

            # Create prompt for advice
            prompt = f"""
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

            # Call LLM
            logger.info(f"Generating advice for TODO {index + 1}/{total}: {title}")
            response = self.model.generate_content(prompt)
            advice = response.text.strip()

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


# Create node instance
todo_advisor_node = TodoAdvisorNode()


async def todo_advisor_handler(input_data: TodoAdvisorInput) -> Dict[str, Any]:
    """Handler function for TODO Advisor node"""
    result = await todo_advisor_node.execute(input_data.model_dump())
    return result.model_dump()
