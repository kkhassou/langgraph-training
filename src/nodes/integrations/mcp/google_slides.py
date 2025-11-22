"""Google Slides MCP Node - Handles Google Slides operations via MCP server"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from src.mcp.google.slides.client import SlidesMCPService
from src.nodes.base import BaseNode, NodeResult

logger = logging.getLogger(__name__)


class SlidesMCPInput(BaseModel):
    """Input schema for Google Slides MCP node"""
    action: str = Field(..., description="Action to perform: create_presentation, read_presentation, add_slide, add_text_to_slide, delete_slide")

    # Common parameters
    presentation_id: Optional[str] = Field(None, description="Presentation ID (from URL)")

    # For create_presentation
    title: Optional[str] = Field("Untitled Presentation", description="Presentation title")

    # For add_slide
    index: Optional[int] = Field(None, description="Position to insert slide")

    # For add_text_to_slide
    slide_id: Optional[str] = Field(None, description="Slide object ID")
    text: Optional[str] = Field(None, description="Text content")


class SlidesMCPNode(BaseNode):
    """Node for Google Slides operations via MCP server"""

    def __init__(self):
        super().__init__("slides-mcp")
        self.slides_service = SlidesMCPService()

    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """Execute Google Slides MCP node"""
        try:
            action = input_data.get("action")

            if action == "create_presentation":
                title = input_data.get("title", "Untitled Presentation")
                result = await self.slides_service.create_presentation(title)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "create_presentation", "title": title}
                )

            elif action == "read_presentation":
                presentation_id = input_data.get("presentation_id")
                if not presentation_id:
                    raise ValueError("presentation_id is required for read_presentation action")

                result = await self.slides_service.read_presentation(presentation_id)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "read_presentation", "presentation_id": presentation_id}
                )

            elif action == "add_slide":
                presentation_id = input_data.get("presentation_id")
                index = input_data.get("index")

                if not presentation_id:
                    raise ValueError("presentation_id is required for add_slide action")

                result = await self.slides_service.add_slide(presentation_id, index)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "add_slide", "presentation_id": presentation_id}
                )

            elif action == "add_text_to_slide":
                presentation_id = input_data.get("presentation_id")
                slide_id = input_data.get("slide_id")
                text = input_data.get("text")

                if not presentation_id:
                    raise ValueError("presentation_id is required for add_text_to_slide action")
                if not slide_id:
                    raise ValueError("slide_id is required for add_text_to_slide action")
                if not text:
                    raise ValueError("text is required for add_text_to_slide action")

                result = await self.slides_service.add_text_to_slide(
                    presentation_id, slide_id, text
                )
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "add_text_to_slide", "presentation_id": presentation_id}
                )

            elif action == "delete_slide":
                presentation_id = input_data.get("presentation_id")
                slide_id = input_data.get("slide_id")

                if not presentation_id:
                    raise ValueError("presentation_id is required for delete_slide action")
                if not slide_id:
                    raise ValueError("slide_id is required for delete_slide action")

                result = await self.slides_service.delete_slide(presentation_id, slide_id)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "delete_slide", "presentation_id": presentation_id}
                )

            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Error in Slides MCP node: {e}")
            return NodeResult(
                success=False,
                error=str(e),
                metadata={"action": input_data.get("action")}
            )

    async def cleanup(self):
        """Cleanup Slides MCP resources"""
        try:
            await self.slides_service.disconnect()
        except Exception as e:
            logger.error(f"Error during Slides MCP cleanup: {e}")


# Create node instance
slides_mcp_node = SlidesMCPNode()


async def slides_mcp_node_handler(input_data: SlidesMCPInput) -> Dict[str, Any]:
    """Handler function for Google Slides MCP node endpoint"""
    result = await slides_mcp_node.execute(input_data.model_dump())
    return result.model_dump()
