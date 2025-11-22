"""Google Keep Integration Node

Google Keepとの統合を行うノード実装。
MCP (Model Context Protocol) サーバーを介してGoogle APIと通信します。
"""



from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from src.mcp.google.keep.client import KeepMCPService
from src.nodes.base import BaseNode, NodeResult

logger = logging.getLogger(__name__)


class KeepInput(BaseModel):
    """Input schema for Google Keep MCP node"""
    action: str = Field(..., description="Action to perform: create_note, list_notes, get_note, update_note, delete_note")

    # Common parameters
    note_id: Optional[str] = Field(None, description="Note ID")

    # For create_note and update_note
    title: Optional[str] = Field(None, description="Note title")
    body: Optional[str] = Field(None, description="Note body content")

    # For list_notes
    page_size: Optional[int] = Field(10, description="Number of notes to retrieve (max: 100)")


class KeepNode(BaseNode):
    """Node for Google Keep operations via MCP (Model Context Protocol) server"""

    def __init__(self):
        super().__init__("keep-mcp")
        self.keep_service = KeepMCPService()

    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """Execute Google Keep MCP node"""
        try:
            action = input_data.get("action")

            if action == "create_note":
                body = input_data.get("body")
                title = input_data.get("title")

                if not body:
                    raise ValueError("body is required for create_note action")

                result = await self.keep_service.create_note(body, title)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "create_note", "title": title}
                )

            elif action == "list_notes":
                page_size = input_data.get("page_size", 10)
                result = await self.keep_service.list_notes(page_size)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "list_notes", "page_size": page_size}
                )

            elif action == "get_note":
                note_id = input_data.get("note_id")
                if not note_id:
                    raise ValueError("note_id is required for get_note action")

                result = await self.keep_service.get_note(note_id)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "get_note", "note_id": note_id}
                )

            elif action == "update_note":
                note_id = input_data.get("note_id")
                title = input_data.get("title")
                body = input_data.get("body")

                if not note_id:
                    raise ValueError("note_id is required for update_note action")

                result = await self.keep_service.update_note(note_id, title, body)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "update_note", "note_id": note_id}
                )

            elif action == "delete_note":
                note_id = input_data.get("note_id")
                if not note_id:
                    raise ValueError("note_id is required for delete_note action")

                result = await self.keep_service.delete_note(note_id)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "delete_note", "note_id": note_id}
                )

            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Error in Keep MCP node: {e}")
            return NodeResult(
                success=False,
                error=str(e),
                metadata={"action": input_data.get("action")}
            )

    async def cleanup(self):
        """Cleanup Keep MCP resources"""
        try:
            await self.keep_service.disconnect()
        except Exception as e:
            logger.error(f"Error during Keep MCP cleanup: {e}")


# Create node instance
keep_node = KeepNode()


async def keep_node_handler(input_data: KeepInput) -> Dict[str, Any]:
    """Handler function for Google Keep MCP node endpoint"""
    result = await keep_node.execute(input_data.model_dump())
    return result.model_dump()
