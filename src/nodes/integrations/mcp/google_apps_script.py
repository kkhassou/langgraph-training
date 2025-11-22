"""Google Apps Script MCP Node - Handles Google Apps Script operations via MCP server"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import logging

from src.mcp.google.apps_script.client import AppsScriptMCPService
from src.nodes.base import BaseNode, NodeResult

logger = logging.getLogger(__name__)


class AppsScriptMCPInput(BaseModel):
    """Input schema for Google Apps Script MCP node"""
    action: str = Field(..., description="Action to perform: create_project, get_project, update_project, run_function, list_deployments")

    # Common parameters
    script_id: Optional[str] = Field(None, description="Script project ID")

    # For create_project
    title: Optional[str] = Field(None, description="Project title")

    # For update_project
    file_name: Optional[str] = Field(None, description="File name (e.g., 'Code.gs')")
    file_type: Optional[str] = Field("SERVER_JS", description="File type: SERVER_JS, HTML, JSON")
    source: Optional[str] = Field(None, description="File source code")

    # For run_function
    function_name: Optional[str] = Field(None, description="Function name to execute")
    parameters: Optional[List[Any]] = Field(None, description="Function parameters")


class AppsScriptMCPNode(BaseNode):
    """Node for Google Apps Script operations via MCP server"""

    def __init__(self):
        super().__init__("apps-script-mcp")
        self.script_service = AppsScriptMCPService()

    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """Execute Google Apps Script MCP node"""
        try:
            action = input_data.get("action")

            if action == "create_project":
                title = input_data.get("title", "Untitled Project")
                result = await self.script_service.create_project(title)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "create_project", "title": title}
                )

            elif action == "get_project":
                script_id = input_data.get("script_id")
                if not script_id:
                    raise ValueError("script_id is required for get_project action")

                result = await self.script_service.get_project(script_id)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "get_project", "script_id": script_id}
                )

            elif action == "update_project":
                script_id = input_data.get("script_id")
                file_name = input_data.get("file_name")
                file_type = input_data.get("file_type", "SERVER_JS")
                source = input_data.get("source")

                if not script_id:
                    raise ValueError("script_id is required for update_project action")
                if not file_name:
                    raise ValueError("file_name is required for update_project action")
                if not source:
                    raise ValueError("source is required for update_project action")

                result = await self.script_service.update_project(
                    script_id, file_name, file_type, source
                )
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "update_project", "script_id": script_id}
                )

            elif action == "run_function":
                script_id = input_data.get("script_id")
                function_name = input_data.get("function_name")
                parameters = input_data.get("parameters")

                if not script_id:
                    raise ValueError("script_id is required for run_function action")
                if not function_name:
                    raise ValueError("function_name is required for run_function action")

                result = await self.script_service.run_function(
                    script_id, function_name, parameters
                )
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "run_function", "script_id": script_id, "function": function_name}
                )

            elif action == "list_deployments":
                script_id = input_data.get("script_id")
                if not script_id:
                    raise ValueError("script_id is required for list_deployments action")

                result = await self.script_service.list_deployments(script_id)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "list_deployments", "script_id": script_id}
                )

            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Error in Apps Script MCP node: {e}")
            return NodeResult(
                success=False,
                error=str(e),
                metadata={"action": input_data.get("action")}
            )

    async def cleanup(self):
        """Cleanup Apps Script MCP resources"""
        try:
            await self.script_service.disconnect()
        except Exception as e:
            logger.error(f"Error during Apps Script MCP cleanup: {e}")


# Create node instance
apps_script_mcp_node = AppsScriptMCPNode()


async def apps_script_mcp_node_handler(input_data: AppsScriptMCPInput) -> Dict[str, Any]:
    """Handler function for Google Apps Script MCP node endpoint"""
    result = await apps_script_mcp_node.execute(input_data.model_dump())
    return result.model_dump()
