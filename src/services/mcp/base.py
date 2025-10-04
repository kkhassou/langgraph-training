from typing import Dict, Any, Optional, List
import json
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """Base exception for MCP-related errors"""
    pass


class MCPConnectionError(MCPError):
    """Raised when MCP server connection fails"""
    pass


class MCPToolError(MCPError):
    """Raised when MCP tool execution fails"""
    pass


class BaseMCPClient(ABC):
    """Base class for MCP clients"""

    def __init__(self, server_name: str):
        self.server_name = server_name
        self.connected = False
        self.tools = {}

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to MCP server"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from MCP server"""
        pass

    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on the MCP server"""
        pass

    @abstractmethod
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from MCP server"""
        pass

    def is_connected(self) -> bool:
        """Check if client is connected to server"""
        return self.connected