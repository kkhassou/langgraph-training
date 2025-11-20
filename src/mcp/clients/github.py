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


class GitHubMCPClient(BaseMCPClient):
    """GitHub MCP client for real MCP server communication"""

    def __init__(self, server_config: Optional[Dict[str, Any]] = None):
        super().__init__("github")
        self.server_config = server_config or {}
        self.session: Optional[ClientSession] = None
        self.stdio_transport = None
        self.read_stream = None
        self.write_stream = None

    async def connect(self) -> bool:
        """Connect to real GitHub MCP server"""
        if not MCP_AVAILABLE:
            logger.error("MCP library not available")
            return False

        try:
            server_script = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "mcp/servers", "github", "server.py"
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
            logger.info(f"GitHub MCP server initialized: {init_result}")

            self.connected = True
            logger.info("Successfully connected to GitHub MCP server")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to GitHub MCP server: {e}")
            await self.disconnect()
            return False

    async def disconnect(self) -> None:
        """Disconnect from real GitHub MCP server"""
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
            logger.info("Disconnected from GitHub MCP server")

        except Exception as e:
            logger.error(f"Error during disconnection: {e}")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool on real GitHub MCP server"""
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
        """Get tools from real GitHub MCP server"""
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


def get_github_mcp_client() -> BaseMCPClient:
    """Factory function to get GitHub MCP client"""
    if not MCP_AVAILABLE:
        try:
            import mcp
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            logger.info("MCP library dynamically imported successfully")
            return GitHubMCPClient()
        except ImportError as e:
            logger.error(f"MCP library still not available: {e}")
            raise MCPConnectionError(f"MCP library not available. Please install with: pip install mcp")

    logger.info("Using real GitHub MCP client")
    return GitHubMCPClient()


class GitHubMCPService:
    """Service layer for GitHub MCP operations"""

    def __init__(self):
        self.client = get_github_mcp_client()
        self.connected = False

    async def ensure_connected(self):
        """Ensure MCP client is connected"""
        if not self.connected:
            success = await self.client.connect()
            if success:
                self.connected = True
            else:
                raise MCPConnectionError("Failed to connect to GitHub MCP server")

    async def get_repository(self, repo: str) -> Dict[str, Any]:
        """Get repository information"""
        await self.ensure_connected()
        return await self.client.call_tool("get_repository", {"repo": repo})

    async def list_issues(self, repo: str, state: str = "open", limit: int = 10) -> Dict[str, Any]:
        """List repository issues"""
        await self.ensure_connected()
        return await self.client.call_tool("list_issues", {
            "repo": repo,
            "state": state,
            "limit": limit
        })

    async def create_issue(
        self,
        repo: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a new issue"""
        await self.ensure_connected()
        params = {"repo": repo, "title": title}
        if body:
            params["body"] = body
        if labels:
            params["labels"] = labels
        return await self.client.call_tool("create_issue", params)

    async def get_file(self, repo: str, path: str, branch: str = "main") -> Dict[str, Any]:
        """Get file content"""
        await self.ensure_connected()
        return await self.client.call_tool("get_file", {
            "repo": repo,
            "path": path,
            "branch": branch
        })

    async def create_pull_request(
        self,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a pull request"""
        await self.ensure_connected()
        params = {
            "repo": repo,
            "title": title,
            "head": head,
            "base": base
        }
        if body:
            params["body"] = body
        return await self.client.call_tool("create_pull_request", params)

    async def list_pull_requests(self, repo: str, state: str = "open", limit: int = 10) -> Dict[str, Any]:
        """List repository pull requests"""
        await self.ensure_connected()
        return await self.client.call_tool("list_pull_requests", {
            "repo": repo,
            "state": state,
            "limit": limit
        })

    async def search_repositories(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search repositories"""
        await self.ensure_connected()
        return await self.client.call_tool("search_repositories", {
            "query": query,
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
