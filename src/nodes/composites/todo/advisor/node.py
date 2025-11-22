"""TODO Advisor Node - Generates advice for individual TODO items using LLM"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from src.nodes.base import BaseNode, NodeResult
from src.core.providers.llm import LLMProvider
from src.core.exceptions import (
    NodeExecutionError,
    NodeInputValidationError,
    LLMProviderError
)

logger = logging.getLogger(__name__)


class TodoAdvisorInput(BaseModel):
    """Input schema for TODO Advisor node"""
    todo: Dict[str, Any] = Field(..., description="TODO item to advise on")
    index: int = Field(..., description="Index of this TODO in the list")
    total: int = Field(..., description="Total number of TODOs")


class TodoAdvisorNode(BaseNode):
    """Node that generates advice for a single TODO item using LLM Provider
    
    依存性注入パターンを使用し、任意のLLMProviderを注入できます。
    テスト時にモックプロバイダーを使用することも可能です。
    """

    def __init__(self, provider: Optional[LLMProvider] = None):
        super().__init__("todo-advisor")
        # プロバイダーが指定されなければデフォルトを使用
        if provider is None:
            from src.core.factory import ProviderFactory
            provider = ProviderFactory.get_default_llm_provider()
        self.provider = provider

    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """Generate advice for a TODO item
        
        Raises:
            NodeInputValidationError: 入力が不正な場合
            NodeExecutionError: 実行に失敗した場合
        """
        try:
            todo = input_data.get("todo", {})
            index = input_data.get("index", 0)
            total = input_data.get("total", 1)

            # 入力検証
            if not todo:
                raise NodeInputValidationError(
                    "TODO item is required",
                    details={
                        "node": self.name,
                        "index": index,
                        "total": total
                    }
                )
            
            if not isinstance(todo, dict):
                raise NodeInputValidationError(
                    "TODO item must be a dictionary",
                    details={
                        "node": self.name,
                        "todo_type": type(todo).__name__
                    }
                )

            title = todo.get("title", "")
            
            # プロンプト作成（ビジネスロジックに集中）
            prompt = self._create_advice_prompt(todo)
            
            # ✅ LLMProviderを使ってシンプルに呼び出し
            logger.info(f"Generating advice for TODO {index + 1}/{total}: {title}")
            advice = await self.provider.generate(
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

        except NodeInputValidationError:
            raise
        except LLMProviderError as e:
            raise NodeExecutionError(
                f"LLM provider error while generating advice",
                details={
                    "node": self.name,
                    "todo_title": title,
                    "index": index,
                    "error_details": e.details if hasattr(e, 'details') else {}
                },
                original_error=e
            )
        except Exception as e:
            logger.error(f"Unexpected error generating advice: {e}")
            raise NodeExecutionError(
                f"Unexpected error in {self.name}",
                details={
                    "node": self.name,
                    "todo_title": title if 'title' in locals() else "unknown",
                    "index": index,
                    "error_type": type(e).__name__
                },
                original_error=e
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
