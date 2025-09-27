import asyncio
import json
from typing import Dict, Any, List, Optional
from mcp_client import MCPClient
from mcp_client.stdio import stdio_client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class MCPServerClient:
    """Base MCP server client for interacting with MCP servers"""

    def __init__(self, server_name: str, command: List[str], env: Optional[Dict[str, str]] = None):
        self.server_name = server_name
        self.command = command
        self.env = env or {}
        self.client = None
        self._session = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()

    async def connect(self):
        """Connect to the MCP server"""
        try:
            # Start the MCP server process and create client
            self._session = stdio_client(self.command, env=self.env)
            self.client = await self._session.__aenter__()

            # Initialize the server
            await self.client.initialize()

            logger.info(f"Connected to MCP server: {self.server_name}")

        except Exception as e:
            logger.error(f"Failed to connect to MCP server {self.server_name}: {str(e)}")
            raise

    async def disconnect(self):
        """Disconnect from the MCP server"""
        try:
            if self._session:
                await self._session.__aexit__(None, None, None)
                logger.info(f"Disconnected from MCP server: {self.server_name}")
        except Exception as e:
            logger.error(f"Error disconnecting from MCP server {self.server_name}: {str(e)}")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the MCP server"""
        if not self.client:
            raise RuntimeError("MCP client not connected")

        try:
            response = await self.client.list_tools()
            return response.tools
        except Exception as e:
            logger.error(f"Error listing tools from {self.server_name}: {str(e)}")
            raise

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        if not self.client:
            raise RuntimeError("MCP client not connected")

        try:
            response = await self.client.call_tool(tool_name, arguments)
            return {
                "content": response.content,
                "isError": response.isError
            }
        except Exception as e:
            logger.error(f"Error calling tool {tool_name} on {self.server_name}: {str(e)}")
            raise

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources from the MCP server"""
        if not self.client:
            raise RuntimeError("MCP client not connected")

        try:
            response = await self.client.list_resources()
            return response.resources
        except Exception as e:
            logger.error(f"Error listing resources from {self.server_name}: {str(e)}")
            raise

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource from the MCP server"""
        if not self.client:
            raise RuntimeError("MCP client not connected")

        try:
            response = await self.client.read_resource(uri)
            return {
                "contents": response.contents
            }
        except Exception as e:
            logger.error(f"Error reading resource {uri} from {self.server_name}: {str(e)}")
            raise


class MCPClientManager:
    """Manager for multiple MCP server clients"""

    def __init__(self):
        self.clients: Dict[str, MCPServerClient] = {}
        self.server_configs = self._load_server_configs()

    def _load_server_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load MCP server configurations"""
        try:
            config_path = "config/mcp_config.json"
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("MCP config file not found, using default configurations")
            return self._default_server_configs()
        except Exception as e:
            logger.error(f"Error loading MCP config: {str(e)}")
            return self._default_server_configs()

    def _default_server_configs(self) -> Dict[str, Dict[str, Any]]:
        """Default MCP server configurations"""
        return {
            "slack": {
                "command": ["python", "mcp_servers/slack/server.py"],
                "env": {
                    "SLACK_TOKEN": settings.slack_token or ""
                }
            },
            "jira": {
                "command": ["python", "mcp_servers/jira/server.py"],
                "env": {
                    "JIRA_TOKEN": settings.jira_token or "",
                    "JIRA_SERVER": settings.jira_server or "",
                    "JIRA_EMAIL": settings.jira_email or ""
                }
            }
        }

    async def get_client(self, server_name: str) -> MCPServerClient:
        """Get or create an MCP client for the specified server"""
        if server_name not in self.clients:
            if server_name not in self.server_configs:
                raise ValueError(f"Unknown MCP server: {server_name}")

            config = self.server_configs[server_name]
            self.clients[server_name] = MCPServerClient(
                server_name=server_name,
                command=config["command"],
                env=config.get("env", {})
            )

        return self.clients[server_name]

    async def disconnect_all(self):
        """Disconnect all MCP clients"""
        for client in self.clients.values():
            await client.disconnect()
        self.clients.clear()


# Global MCP client manager instance
mcp_manager = MCPClientManager()