from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from src.nodes.base import BaseNode, NodeState
import logging

logger = logging.getLogger(__name__)


class MCPBaseNode(BaseNode):
    """Base class for MCP-integrated nodes"""

    def __init__(self, name: str, mcp_server_name: str, description: str = ""):
        super().__init__(name, description)
        self.mcp_server_name = mcp_server_name

    async def get_mcp_client(self):
        """Get MCP client for this node's server - placeholder method"""
        logger.warning(f"MCP client functionality not implemented for {self.mcp_server_name}")
        return None

    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server - placeholder method"""
        logger.warning(f"MCP tool calling not implemented: {tool_name}")
        return {"error": "MCP functionality not available"}

    async def list_mcp_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the MCP server - placeholder method"""
        logger.warning("MCP tools listing not implemented")
        return []

    def handle_mcp_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """Handle MCP-specific errors"""
        error_msg = f"MCP error in {self.name}"
        if context:
            error_msg += f" ({context})"
        error_msg += f": {str(error)}"

        logger.error(error_msg)
        return {"error": error_msg}

    async def execute(self, state: NodeState) -> NodeState:
        """Execute the MCP node logic"""
        try:
            # Call the specific MCP implementation
            result = await self.execute_mcp(state)
            return result

        except Exception as e:
            error_info = self.handle_mcp_error(e, "execution")
            state.data.update(error_info)
            state.metadata["error_node"] = self.name
            return state

    @abstractmethod
    async def execute_mcp(self, state: NodeState) -> NodeState:
        """Execute MCP-specific logic (to be implemented by subclasses)"""
        pass

    def get_info(self) -> Dict[str, str]:
        """Get node information including MCP server details"""
        info = super().get_info()
        info.update({
            "mcp_server": self.mcp_server_name,
            "integration_type": "mcp"
        })
        return info