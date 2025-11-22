"""TODO Parser Node - Parses email content into individual TODO items using LLM"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
import logging

from src.nodes.base import BaseNode, NodeResult
from src.services.llm.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class TodoItem(BaseModel):
    """Individual TODO item"""
    title: str
    description: str
    priority: str = "medium"
    estimated_time: int = 30


class TodoList(BaseModel):
    """List of TODO items"""
    todos: List[TodoItem]


class TodoParserInput(BaseModel):
    """Input schema for TODO Parser node"""
    email_content: str = Field(..., description="Email content to parse")
    sender: str = Field(..., description="Email sender")


class TodoParserNode(BaseNode):
    """Node that parses email content into TODO items using LLM"""

    def __init__(self):
        super().__init__("todo-parser")

    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """Parse email content into TODO items"""
        try:
            email_content = input_data.get("email_content", "")
            sender = input_data.get("sender", "")

            logger.info(f"TODO Parser received - sender: '{sender}', content length: {len(email_content)}")

            # プロンプト作成（ビジネスロジックに集中）
            prompt = self._create_parser_prompt(email_content, sender)

            # ✅ GeminiServiceを使ってJSON生成
            logger.info("Calling Gemini to parse TODO items")
            result = await GeminiService.generate_json(
                prompt=prompt,
                schema=TodoList,
                temperature=0.7
            )

            # TodoListからリストに変換
            todos = [todo.dict() for todo in result.todos]

            logger.info(f"Parsed {len(todos)} TODO items from email")

            return NodeResult(
                success=True,
                data={
                    "todos": todos,
                    "count": len(todos),
                    "original_email": email_content,
                    "sender": sender
                },
                metadata={
                    "action": "parse_todos",
                    "count": len(todos)
                }
            )

        except Exception as e:
            logger.error(f"Error in TODO parser: {e}")
            return NodeResult(
                success=False,
                error=str(e),
                metadata={"action": "parse_todos"}
            )

    def _create_parser_prompt(self, email_content: str, sender: str) -> str:
        """プロンプト作成（ビジネスロジックに集中）"""
        return f"""
あなたは優秀なタスク管理アシスタントです。
以下のメール内容から、翌日のTODOリストを抽出してください。

メール送信者: {sender}
メール内容: {email_content}

各TODOについて以下の情報を推定してください：
- title: 簡潔なタスク名
- description: タスクの内容
- priority: high/medium/low（指定がなければmedium）
- estimated_time: 分単位（指定がなければ30）
"""


# Create node instance
todo_parser_node = TodoParserNode()


async def todo_parser_handler(input_data: TodoParserInput) -> Dict[str, Any]:
    """Handler function for TODO Parser node"""
    result = await todo_parser_node.execute(input_data.model_dump())
    return result.model_dump()
