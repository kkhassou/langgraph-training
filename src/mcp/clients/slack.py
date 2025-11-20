from typing import Dict, Any, Optional, List
import logging
import asyncio
import subprocess
import json
import sys
import os
from .base import BaseMCPClient,  MCPConnectionError, MCPToolError

logger = logging.getLogger(__name__)

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
    logger.info("MCP library successfully imported")
except ImportError as e:
    MCP_AVAILABLE = False
    logger.error(f"MCP library import failed: {e}")
    # フォールバック: 動的インポートを試行
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None


class SlackMCPClient(BaseMCPClient):
    """Slack MCP client for real MCP server communication"""

    def __init__(self, server_config: Optional[Dict[str, Any]] = None):
        super().__init__("slack")
        self.server_config = server_config or {}
        self.session: Optional[ClientSession] = None
        self.stdio_transport = None
        self.read_stream = None
        self.write_stream = None

    async def connect(self) -> bool:
        """Connect to real Slack MCP server"""
        if not MCP_AVAILABLE:
            logger.error("MCP library not available")
            return False

        try:
            # Path to our Slack MCP server (use the app version which has get_channels)
            server_script = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "mcp/servers", "slack", "server.py"
            )
            server_script = os.path.abspath(server_script)

            if not os.path.exists(server_script):
                logger.error(f"MCP server script not found: {server_script}")
                return False

            # Create server parameters
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[server_script],
                env=dict(os.environ)  # Pass current environment variables
            )

            # Connect to the server using context manager
            self.stdio_transport = stdio_client(server_params)
            self.read_stream, self.write_stream = await self.stdio_transport.__aenter__()

            # Create session
            from mcp import ClientSession
            self.session = ClientSession(self.read_stream, self.write_stream)

            # Initialize the session
            await self.session.__aenter__()

            # Initialize the connection
            init_result = await self.session.initialize()
            logger.info(f"MCP server initialized: {init_result}")

            self.connected = True
            logger.info("Successfully connected to Slack MCP server")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            await self.disconnect()
            return False

    async def disconnect(self) -> None:
        """Disconnect from real Slack MCP server"""
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
                self.session = None

            if self.stdio_transport:
                await self.stdio_transport.__aexit__(None, None, None)
                self.stdio_transport = None

            self.read_stream = None
            self.write_stream = None
            self.connected = False
            logger.info("Disconnected from Slack MCP server")

        except Exception as e:
            logger.error(f"Error during disconnection: {e}")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool on real Slack MCP server"""
        if not self.connected or not self.session:
            raise MCPConnectionError("Not connected to MCP server")

        try:
            # Call the tool using MCP session
            result = await self.session.call_tool(tool_name, arguments)

            # Convert MCP result to our expected format
            if result and result.content:
                content_text = ""
                for content_item in result.content:
                    if hasattr(content_item, 'text'):
                        content_text += content_item.text + "\n"

                return {
                    "content": [{"type": "text", "text": content_text.strip()}],
                    "isError": result.isError if hasattr(result, 'isError') else False,
                    "tool_result": result  # Include raw result for additional processing
                }
            else:
                return {
                    "content": [{"type": "text", "text": "Tool executed successfully but returned no content"}],
                    "isError": False
                }

        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            raise MCPToolError(f"Tool execution failed: {str(e)}")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get tools from real Slack MCP server"""
        if not self.connected or not self.session:
            raise MCPConnectionError("Not connected to MCP server")

        try:
            # List tools using MCP session
            tools_result = await self.session.list_tools()

            # Convert to our expected format
            tools = []
            for tool in tools_result.tools:
                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                })

            return tools

        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            raise MCPToolError(f"Failed to list tools: {str(e)}")


def get_slack_mcp_client(use_mock: bool = True) -> BaseMCPClient:
    """Factory function to get Slack MCP client"""
    # 動的にMCPライブラリの利用可能性をチェック
    if not MCP_AVAILABLE:
        try:
            # 再度インポートを試行
            import mcp
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            logger.info("MCP library dynamically imported successfully")
            return SlackMCPClient()
        except ImportError as e:
            logger.error(f"MCP library still not available: {e}")
            raise MCPConnectionError(f"MCP library not available. Please install with: pip install mcp")
    
    logger.info("Using real Slack MCP client")
    return SlackMCPClient()


class SlackMCPService:
    """Service layer for Slack MCP operations"""

    def __init__(self, use_mock: bool = True):
        self.client = get_slack_mcp_client(use_mock)
        self.connected = False
        self.use_mock = use_mock

    async def ensure_connected(self):
        """Ensure MCP client is connected"""
        if not self.connected:
            success = await self.client.connect()
            if success:
                self.connected = True
            else:
                raise MCPConnectionError("Failed to connect to Slack MCP server")

    async def get_channels(self) -> Dict[str, Any]:
        """Get Slack channels via MCP"""
        await self.ensure_connected()
        return await self.client.call_tool("get_channels", {})

    async def send_message(self, channel: str, text: str) -> Dict[str, Any]:
        """Send message to Slack channel via MCP"""
        await self.ensure_connected()
        return await self.client.call_tool("send_message", {
            "channel": channel,
            "text": text
        })

    async def get_messages(self, channel: str, limit: int = 10, days_back: int = 7) -> Dict[str, Any]:
        """Get messages from Slack channel via MCP"""
        await self.ensure_connected()
        return await self.client.call_tool("get_messages", {
            "channel": channel,
            "limit": limit
        })

    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """List available MCP tools"""
        await self.ensure_connected()
        return await self.client.list_tools()

    async def disconnect(self):
        """Disconnect from MCP server"""
        if self.connected:
            await self.client.disconnect()
            self.connected = False