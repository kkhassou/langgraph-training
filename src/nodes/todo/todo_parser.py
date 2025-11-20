"""TODO Parser Node - Parses email content into individual TODO items using LLM"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
import logging
import os
import json

from src.nodes.base import BaseNode, NodeResult

logger = logging.getLogger(__name__)

# Import Gemini for LLM parsing
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google-generativeai not available")


class TodoParserInput(BaseModel):
    """Input schema for TODO Parser node"""
    email_content: str = Field(..., description="Email content to parse")
    sender: str = Field(..., description="Email sender")


class TodoParserNode(BaseNode):
    """Node that parses email content into TODO items using LLM"""

    def __init__(self):
        super().__init__("todo-parser")
        self.api_key = os.getenv("GEMINI_API_KEY")

        if GENAI_AVAILABLE and self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        else:
            self.model = None
            logger.warning("Gemini model not configured")

    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """Parse email content into TODO items"""
        try:
            email_content = input_data.get("email_content", "")
            sender = input_data.get("sender", "")

            print(f"[DEBUG] TODO Parser received - input_data: {input_data}")
            print(f"[DEBUG] sender: '{sender}', content: '{email_content}'")
            logger.info(f"TODO Parser received - sender: '{sender}', content length: {len(email_content)}")
            logger.info(f"Email content: {email_content[:100] if email_content else '(empty)'}")

            if not self.model:
                raise ValueError("Gemini model not configured. Please set GEMINI_API_KEY")

            # Create prompt for LLM
            prompt = f"""あなたは優秀なタスク管理アシスタントです。
以下のメール内容から、翌日のTODOリストを抽出してください。

メール送信者: {sender}
メール内容: {email_content}

各TODOについて以下の情報を推定してください：
- タイトル: 簡潔なタスク名
- 詳細説明: タスクの内容
- 優先度: high/medium/low（指定がなければmedium）
- 予想所要時間: 分単位（指定がなければ30）

以下のJSON形式でのみ返答してください。他の説明は一切含めないでください：
{{
  "todos": [
    {{
      "title": "タスクのタイトル",
      "description": "タスクの詳細説明",
      "priority": "medium",
      "estimated_time": 30
    }}
  ]
}}"""

            # Call LLM
            logger.info("Calling Gemini to parse TODO items")
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            # Parse JSON response
            parsed_data = json.loads(response_text)
            todos = parsed_data.get("todos", [])

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

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response was: {response_text}")
            return NodeResult(
                success=False,
                error=f"Failed to parse LLM response: {str(e)}",
                metadata={"action": "parse_todos"}
            )
        except Exception as e:
            logger.error(f"Error in TODO parser: {e}")
            return NodeResult(
                success=False,
                error=str(e),
                metadata={"action": "parse_todos"}
            )


# Create node instance
todo_parser_node = TodoParserNode()


async def todo_parser_handler(input_data: TodoParserInput) -> Dict[str, Any]:
    """Handler function for TODO Parser node"""
    result = await todo_parser_node.execute(input_data.model_dump())
    return result.model_dump()
