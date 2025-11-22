"""Google Sheets MCP Node - Handles Google Sheets operations via MCP server"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import logging

from src.mcp.google.sheets.client import SheetsMCPService
from src.nodes.base import BaseNode, NodeResult

logger = logging.getLogger(__name__)


class SheetsMCPInput(BaseModel):
    """Input schema for Google Sheets MCP node"""
    action: str = Field(..., description="Action to perform: create_spreadsheet, read_range, write_range, append_rows, clear_range, get_spreadsheet_info")

    # Common parameters
    spreadsheet_id: Optional[str] = Field(None, description="Spreadsheet ID (from URL)")

    # For create_spreadsheet
    title: Optional[str] = Field("Untitled Spreadsheet", description="Spreadsheet title")

    # For range operations
    range: Optional[str] = Field(None, description="Range in A1 notation (e.g., 'Sheet1!A1:D10')")

    # For write_range and append_rows
    values: Optional[List[List[Any]]] = Field(None, description="2D array of values to write")


class SheetsMCPNode(BaseNode):
    """Node for Google Sheets operations via MCP server"""

    def __init__(self):
        super().__init__("sheets-mcp")
        self.sheets_service = SheetsMCPService()

    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """Execute Google Sheets MCP node"""
        try:
            action = input_data.get("action")

            if action == "create_spreadsheet":
                title = input_data.get("title", "Untitled Spreadsheet")
                result = await self.sheets_service.create_spreadsheet(title)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "create_spreadsheet", "title": title}
                )

            elif action == "read_range":
                spreadsheet_id = input_data.get("spreadsheet_id")
                range_name = input_data.get("range", "Sheet1!A1:Z1000")

                if not spreadsheet_id:
                    raise ValueError("spreadsheet_id is required for read_range action")

                result = await self.sheets_service.read_range(spreadsheet_id, range_name)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "read_range", "spreadsheet_id": spreadsheet_id, "range": range_name}
                )

            elif action == "write_range":
                spreadsheet_id = input_data.get("spreadsheet_id")
                range_name = input_data.get("range", "Sheet1!A1")
                values = input_data.get("values", [])

                if not spreadsheet_id:
                    raise ValueError("spreadsheet_id is required for write_range action")
                if not values:
                    raise ValueError("values are required for write_range action")

                result = await self.sheets_service.write_range(spreadsheet_id, values, range_name)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "write_range", "spreadsheet_id": spreadsheet_id}
                )

            elif action == "append_rows":
                spreadsheet_id = input_data.get("spreadsheet_id")
                range_name = input_data.get("range", "Sheet1!A1")
                values = input_data.get("values", [])

                if not spreadsheet_id:
                    raise ValueError("spreadsheet_id is required for append_rows action")
                if not values:
                    raise ValueError("values are required for append_rows action")

                result = await self.sheets_service.append_rows(spreadsheet_id, values, range_name)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "append_rows", "spreadsheet_id": spreadsheet_id}
                )

            elif action == "clear_range":
                spreadsheet_id = input_data.get("spreadsheet_id")
                range_name = input_data.get("range", "Sheet1!A1:Z1000")

                if not spreadsheet_id:
                    raise ValueError("spreadsheet_id is required for clear_range action")

                result = await self.sheets_service.clear_range(spreadsheet_id, range_name)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "clear_range", "spreadsheet_id": spreadsheet_id}
                )

            elif action == "get_spreadsheet_info":
                spreadsheet_id = input_data.get("spreadsheet_id")

                if not spreadsheet_id:
                    raise ValueError("spreadsheet_id is required for get_spreadsheet_info action")

                result = await self.sheets_service.get_spreadsheet_info(spreadsheet_id)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "get_spreadsheet_info", "spreadsheet_id": spreadsheet_id}
                )

            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Error in Sheets MCP node: {e}")
            return NodeResult(
                success=False,
                error=str(e),
                metadata={"action": input_data.get("action")}
            )

    async def cleanup(self):
        """Cleanup Sheets MCP resources"""
        try:
            await self.sheets_service.disconnect()
        except Exception as e:
            logger.error(f"Error during Sheets MCP cleanup: {e}")


# Create node instance
sheets_mcp_node = SheetsMCPNode()


async def sheets_mcp_node_handler(input_data: SheetsMCPInput) -> Dict[str, Any]:
    """Handler function for Google Sheets MCP node endpoint"""
    result = await sheets_mcp_node.execute(input_data.model_dump())
    return result.model_dump()
