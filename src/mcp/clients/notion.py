from typing import Dict, Any, Optional, List
import logging
import sys
import os
from .base import BaseMCPClient, MCPConnectionError, MCPToolError

logger = logging.getLogger(__name__)

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
    logger.info("MCP library successfully imported")
except ImportError as e:
    MCP_AVAILABLE = False
    logger.error(f"MCP library import failed: {e}")
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None


class NotionMCPClient(BaseMCPClient):
    """Notion MCP client for real MCP server communication"""

    def __init__(self, server_config: Optional[Dict[str, Any]] = None):
        super().__init__("notion")
        self.server_config = server_config or {}
        self.session: Optional[ClientSession] = None
        self.stdio_transport = None
        self.read_stream = None
        self.write_stream = None

    async def connect(self) -> bool:
        """Connect to real Notion MCP server"""
        if not MCP_AVAILABLE:
            logger.error("MCP library not available")
            return False

        try:
            server_script = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "mcp/servers", "notion", "server.py"
            )
            server_script = os.path.abspath(server_script)

            if not os.path.exists(server_script):
                logger.error(f"MCP server script not found: {server_script}")
                return False

            server_params = StdioServerParameters(
                command=sys.executable,
                args=[server_script],
                env=dict(os.environ)
            )

            self.stdio_transport = stdio_client(server_params)
            self.read_stream, self.write_stream = await self.stdio_transport.__aenter__()

            from mcp import ClientSession
            self.session = ClientSession(self.read_stream, self.write_stream)
            await self.session.__aenter__()

            init_result = await self.session.initialize()
            logger.info(f"Notion MCP server initialized: {init_result}")

            self.connected = True
            logger.info("Successfully connected to Notion MCP server")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Notion MCP server: {e}")
            await self.disconnect()
            return False

    async def disconnect(self) -> None:
        """Disconnect from real Notion MCP server"""
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
            logger.info("Disconnected from Notion MCP server")

        except Exception as e:
            logger.error(f"Error during disconnection: {e}")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool on real Notion MCP server"""
        if not self.connected or not self.session:
            raise MCPConnectionError("Not connected to MCP server")

        try:
            result = await self.session.call_tool(tool_name, arguments)

            if result and result.content:
                content_text = ""
                for content_item in result.content:
                    if hasattr(content_item, 'text'):
                        content_text += content_item.text + "\n"

                return {
                    "content": [{"type": "text", "text": content_text.strip()}],
                    "isError": result.isError if hasattr(result, 'isError') else False,
                    "tool_result": result
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
        """Get tools from real Notion MCP server"""
        if not self.connected or not self.session:
            raise MCPConnectionError("Not connected to MCP server")

        try:
            tools_result = await self.session.list_tools()

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


def get_notion_mcp_client() -> BaseMCPClient:
    """Factory function to get Notion MCP client"""
    if not MCP_AVAILABLE:
        try:
            import mcp
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            logger.info("MCP library dynamically imported successfully")
            return NotionMCPClient()
        except ImportError as e:
            logger.error(f"MCP library still not available: {e}")
            raise MCPConnectionError(f"MCP library not available. Please install with: pip install mcp")

    logger.info("Using real Notion MCP client")
    return NotionMCPClient()


class NotionMCPService:
    """Service layer for Notion MCP operations"""

    def __init__(self):
        self.client = get_notion_mcp_client()
        self.connected = False

    async def ensure_connected(self):
        """Ensure MCP client is connected"""
        if not self.connected:
            success = await self.client.connect()
            if success:
                self.connected = True
            else:
                raise MCPConnectionError("Failed to connect to Notion MCP server")

    async def create_page(self, parent_id: str, title: str, content: Optional[str] = None) -> Dict[str, Any]:
        """Create a new page"""
        await self.ensure_connected()
        params = {
            "parent_id": parent_id,
            "title": title
        }
        if content:
            params["content"] = content
        return await self.client.call_tool("create_page", params)

    async def get_page(self, page_id: str) -> Dict[str, Any]:
        """Get page content"""
        await self.ensure_connected()
        return await self.client.call_tool("get_page", {"page_id": page_id})

    async def update_page(self, page_id: str, title: Optional[str] = None) -> Dict[str, Any]:
        """Update page properties"""
        await self.ensure_connected()
        params = {"page_id": page_id}
        if title:
            params["title"] = title
        return await self.client.call_tool("update_page", params)

    async def query_database(
        self,
        database_id: str,
        filter_obj: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, Any]]] = None,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """Query a database"""
        await self.ensure_connected()
        params = {
            "database_id": database_id,
            "page_size": page_size
        }
        if filter_obj:
            params["filter"] = filter_obj
        if sorts:
            params["sorts"] = sorts
        return await self.client.call_tool("query_database", params)

    async def create_database_entry(self, database_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new database entry"""
        await self.ensure_connected()
        return await self.client.call_tool("create_database_entry", {
            "database_id": database_id,
            "properties": properties
        })

    async def search(self, query: str, filter_obj: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Search workspace"""
        await self.ensure_connected()
        params = {"query": query}
        if filter_obj:
            params["filter"] = filter_obj
        return await self.client.call_tool("search", params)

    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """List available MCP tools"""
        await self.ensure_connected()
        return await self.client.list_tools()

    async def disconnect(self):
        """Disconnect from MCP server"""
        if self.connected:
            await self.client.disconnect()
            self.connected = False
