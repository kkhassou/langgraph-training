"""Email Composer Node - Composes email from TODO items with advice"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
import logging

from src.nodes.base import BaseNode, NodeResult

logger = logging.getLogger(__name__)


class EmailComposerInput(BaseModel):
    """Input schema for Email Composer node"""
    advised_todos: List[Dict[str, Any]] = Field(..., description="List of TODOs with advice")
    recipient: str = Field(..., description="Email recipient")
    original_subject: str = Field(default="TODO", description="Original email subject")


class EmailComposerNode(BaseNode):
    """Node that composes an email from advised TODOs"""

    def __init__(self):
        super().__init__("email-composer")

    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """Compose email from advised TODOs"""
        try:
            advised_todos = input_data.get("advised_todos", [])
            recipient = input_data.get("recipient", "")
            original_subject = input_data.get("original_subject", "TODO")

            if not advised_todos:
                raise ValueError("No advised TODOs provided")

            # Sort by index to maintain order
            advised_todos_sorted = sorted(advised_todos, key=lambda x: x.get("index", 0))

            # Compose email body
            email_body = f"明日のTODOリストとアドバイス\n"
            email_body += "=" * 50 + "\n\n"
            email_body += f"合計タスク数: {len(advised_todos_sorted)}件\n\n"

            for item in advised_todos_sorted:
                todo = item.get("todo", {})
                advice = item.get("advice", "")
                index = item.get("index", 0)

                title = todo.get("title", "")
                description = todo.get("description", "")
                priority = todo.get("priority", "medium")
                estimated_time = todo.get("estimated_time", "")

                # Priority emoji
                priority_emoji = {
                    "high": "🔴",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(priority.lower(), "⚪")

                email_body += f"【タスク {index + 1}】{priority_emoji} {title}\n"
                email_body += f"優先度: {priority} | 予想時間: {estimated_time}分\n"
                email_body += f"\n詳細:\n{description}\n"
                email_body += f"\n💡 アドバイス:\n{advice}\n"
                email_body += "\n" + "-" * 50 + "\n\n"

            email_body += "\n頑張ってください！\n"
            email_body += "\n---\n"
            email_body += "このメールはAIアシスタントによって自動生成されました。\n"

            # Create email subject
            subject = f"Re: {original_subject} - TODOアドバイス ({len(advised_todos_sorted)}件)"

            result_data = {
                "recipient": recipient,
                "subject": subject,
                "body": email_body,
                "todo_count": len(advised_todos_sorted)
            }

            logger.info(f"Composed email with {len(advised_todos_sorted)} TODOs")

            return NodeResult(
                success=True,
                data=result_data,
                metadata={
                    "action": "compose_email",
                    "todo_count": len(advised_todos_sorted)
                }
            )

        except Exception as e:
            logger.error(f"Error composing email: {e}")
            return NodeResult(
                success=False,
                error=str(e),
                metadata={"action": "compose_email"}
            )


# Create node instance
email_composer_node = EmailComposerNode()


async def email_composer_handler(input_data: EmailComposerInput) -> Dict[str, Any]:
    """Handler function for Email Composer node"""
    result = await email_composer_node.execute(input_data.model_dump())
    return result.model_dump()
