"""Gmail MCP Node - Handles Gmail operations via MCP server"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from src.services.mcp.gmail import GmailMCPService
from src.nodes.base import BaseNode, NodeResult

logger = logging.getLogger(__name__)


class GmailMCPInput(BaseModel):
    """Input schema for Gmail MCP node"""
    action: str = Field(..., description="Action to perform: watch_inbox, get_messages, send_message")
    topic_name: Optional[str] = Field(None, description="Pub/Sub topic name for watch_inbox")
    query: Optional[str] = Field("", description="Gmail search query for get_messages")
    max_results: Optional[int] = Field(10, description="Maximum number of messages to retrieve")
    to: Optional[str] = Field(None, description="Recipient email for send_message")
    subject: Optional[str] = Field(None, description="Email subject for send_message")
    body: Optional[str] = Field(None, description="Email body for send_message")


class GmailMCPNode(BaseNode):
    """Node for Gmail operations via MCP server"""

    def __init__(self):
        super().__init__("gmail-mcp")
        self.gmail_service = GmailMCPService()

    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """Execute Gmail MCP node"""
        try:
            action = input_data.get("action")

            if action == "watch_inbox":
                topic_name = input_data.get("topic_name")
                if not topic_name:
                    raise ValueError("topic_name is required for watch_inbox action")

                result = await self.gmail_service.watch_inbox(topic_name)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "watch_inbox", "topic": topic_name}
                )

            elif action == "get_messages":
                query = input_data.get("query", "")
                max_results = input_data.get("max_results", 10)

                result = await self.gmail_service.get_messages(query, max_results)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "get_messages", "query": query, "max_results": max_results}
                )

            elif action == "send_message":
                to = input_data.get("to")
                subject = input_data.get("subject")
                body = input_data.get("body")

                if not all([to, subject, body]):
                    raise ValueError("to, subject, and body are required for send_message action")

                result = await self.gmail_service.send_message(to, subject, body)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "send_message", "to": to, "subject": subject}
                )

            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Error in Gmail MCP node: {e}")
            return NodeResult(
                success=False,
                error=str(e),
                metadata={"action": input_data.get("action")}
            )

    async def cleanup(self):
        """Cleanup Gmail MCP resources"""
        try:
            await self.gmail_service.disconnect()
        except Exception as e:
            logger.error(f"Error during Gmail MCP cleanup: {e}")


# Create node instance
gmail_mcp_node = GmailMCPNode()


async def gmail_mcp_node_handler(input_data: GmailMCPInput) -> Dict[str, Any]:
    """Handler function for Gmail MCP node endpoint"""
    result = await gmail_mcp_node.execute(input_data.model_dump())
    return result.model_dump()
