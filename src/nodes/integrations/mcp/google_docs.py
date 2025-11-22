"""Google Docs MCP Node - Handles Google Docs operations via MCP server"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from src.mcp.google.docs.client import DocsMCPService
from src.nodes.base import BaseNode, NodeResult

logger = logging.getLogger(__name__)


class DocsMCPInput(BaseModel):
    """Input schema for Google Docs MCP node"""
    action: str = Field(..., description="Action to perform: create_document, read_document, append_text, insert_text, replace_text")

    # Common parameters
    document_id: Optional[str] = Field(None, description="Document ID (from URL)")

    # For create_document
    title: Optional[str] = Field("Untitled Document", description="Document title")

    # For text operations
    text: Optional[str] = Field(None, description="Text content")
    index: Optional[int] = Field(1, description="Character index for insert_text")

    # For replace_text
    find_text: Optional[str] = Field(None, description="Text to find")
    replace_text: Optional[str] = Field(None, description="Text to replace with")
    match_case: Optional[bool] = Field(False, description="Match case for replace")


class DocsMCPNode(BaseNode):
    """Node for Google Docs operations via MCP server"""

    def __init__(self):
        super().__init__("docs-mcp")
        self.docs_service = DocsMCPService()

    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """Execute Google Docs MCP node"""
        try:
            action = input_data.get("action")

            if action == "create_document":
                title = input_data.get("title", "Untitled Document")
                result = await self.docs_service.create_document(title)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "create_document", "title": title}
                )

            elif action == "read_document":
                document_id = input_data.get("document_id")
                if not document_id:
                    raise ValueError("document_id is required for read_document action")

                result = await self.docs_service.read_document(document_id)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "read_document", "document_id": document_id}
                )

            elif action == "append_text":
                document_id = input_data.get("document_id")
                text = input_data.get("text")

                if not document_id:
                    raise ValueError("document_id is required for append_text action")
                if not text:
                    raise ValueError("text is required for append_text action")

                result = await self.docs_service.append_text(document_id, text)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "append_text", "document_id": document_id}
                )

            elif action == "insert_text":
                document_id = input_data.get("document_id")
                text = input_data.get("text")
                index = input_data.get("index", 1)

                if not document_id:
                    raise ValueError("document_id is required for insert_text action")
                if not text:
                    raise ValueError("text is required for insert_text action")

                result = await self.docs_service.insert_text(document_id, text, index)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "insert_text", "document_id": document_id}
                )

            elif action == "replace_text":
                document_id = input_data.get("document_id")
                find_text = input_data.get("find_text")
                replace_text = input_data.get("replace_text")
                match_case = input_data.get("match_case", False)

                if not document_id:
                    raise ValueError("document_id is required for replace_text action")
                if not find_text:
                    raise ValueError("find_text is required for replace_text action")
                if replace_text is None:
                    raise ValueError("replace_text is required for replace_text action")

                result = await self.docs_service.replace_text(
                    document_id, find_text, replace_text, match_case
                )
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "replace_text", "document_id": document_id}
                )

            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Error in Docs MCP node: {e}")
            return NodeResult(
                success=False,
                error=str(e),
                metadata={"action": input_data.get("action")}
            )

    async def cleanup(self):
        """Cleanup Docs MCP resources"""
        try:
            await self.docs_service.disconnect()
        except Exception as e:
            logger.error(f"Error during Docs MCP cleanup: {e}")


# Create node instance
docs_mcp_node = DocsMCPNode()


async def docs_mcp_node_handler(input_data: DocsMCPInput) -> Dict[str, Any]:
    """Handler function for Google Docs MCP node endpoint"""
    result = await docs_mcp_node.execute(input_data.model_dump())
    return result.model_dump()
