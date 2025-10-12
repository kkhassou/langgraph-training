"""Google Forms MCP Node - Handles Google Forms operations via MCP server"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from src.services.mcp.google_forms import FormsMCPService
from src.nodes.base import BaseNode, NodeResult

logger = logging.getLogger(__name__)


class FormsMCPInput(BaseModel):
    """Input schema for Google Forms MCP node"""
    action: str = Field(..., description="Action to perform: create_form, get_form, list_responses, get_response, update_form")

    # Common parameters
    form_id: Optional[str] = Field(None, description="Form ID (from URL)")

    # For create_form and update_form
    title: Optional[str] = Field("Untitled Form", description="Form title")
    description: Optional[str] = Field(None, description="Form description")

    # For get_response
    response_id: Optional[str] = Field(None, description="Response ID")


class FormsMCPNode(BaseNode):
    """Node for Google Forms operations via MCP server"""

    def __init__(self):
        super().__init__("forms-mcp")
        self.forms_service = FormsMCPService()

    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """Execute Google Forms MCP node"""
        try:
            action = input_data.get("action")

            if action == "create_form":
                title = input_data.get("title", "Untitled Form")
                description = input_data.get("description")
                result = await self.forms_service.create_form(title, description)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "create_form", "title": title}
                )

            elif action == "get_form":
                form_id = input_data.get("form_id")
                if not form_id:
                    raise ValueError("form_id is required for get_form action")

                result = await self.forms_service.get_form(form_id)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "get_form", "form_id": form_id}
                )

            elif action == "list_responses":
                form_id = input_data.get("form_id")
                if not form_id:
                    raise ValueError("form_id is required for list_responses action")

                result = await self.forms_service.list_responses(form_id)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "list_responses", "form_id": form_id}
                )

            elif action == "get_response":
                form_id = input_data.get("form_id")
                response_id = input_data.get("response_id")

                if not form_id:
                    raise ValueError("form_id is required for get_response action")
                if not response_id:
                    raise ValueError("response_id is required for get_response action")

                result = await self.forms_service.get_response(form_id, response_id)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "get_response", "form_id": form_id, "response_id": response_id}
                )

            elif action == "update_form":
                form_id = input_data.get("form_id")
                title = input_data.get("title")
                description = input_data.get("description")

                if not form_id:
                    raise ValueError("form_id is required for update_form action")

                result = await self.forms_service.update_form(form_id, title, description)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "update_form", "form_id": form_id}
                )

            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Error in Forms MCP node: {e}")
            return NodeResult(
                success=False,
                error=str(e),
                metadata={"action": input_data.get("action")}
            )

    async def cleanup(self):
        """Cleanup Forms MCP resources"""
        try:
            await self.forms_service.disconnect()
        except Exception as e:
            logger.error(f"Error during Forms MCP cleanup: {e}")


# Create node instance
forms_mcp_node = FormsMCPNode()


async def forms_mcp_node_handler(input_data: FormsMCPInput) -> Dict[str, Any]:
    """Handler function for Google Forms MCP node endpoint"""
    result = await forms_mcp_node.execute(input_data.model_dump())
    return result.model_dump()
