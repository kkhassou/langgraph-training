from typing import List, Dict, Any, Optional
from app.services.mcp_services.mcp_client import mcp_manager
import logging

logger = logging.getLogger(__name__)


class SlackMCPService:
    """Service for Slack operations using MCP server"""

    def __init__(self):
        self.server_name = "slack"

    async def get_channels(self) -> List[Dict[str, Any]]:
        """Get list of channels via MCP"""
        async with await mcp_manager.get_client(self.server_name) as client:
            result = await client.call_tool("list_channels", {})

            if result.get("isError"):
                raise Exception(f"MCP error: {result.get('content', 'Unknown error')}")

            return result.get("content", {}).get("channels", [])

    async def get_messages(
        self,
        channel_id: str,
        limit: int = 100,
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """Get messages from a channel via MCP"""
        async with await mcp_manager.get_client(self.server_name) as client:
            result = await client.call_tool("get_messages", {
                "channel_id": channel_id,
                "limit": limit,
                "days_back": days_back
            })

            if result.get("isError"):
                raise Exception(f"MCP error: {result.get('content', 'Unknown error')}")

            return result.get("content", {}).get("messages", [])

    async def post_message(
        self,
        channel_id: str,
        text: str,
        thread_ts: Optional[str] = None
    ) -> Dict[str, Any]:
        """Post a message to a channel via MCP"""
        async with await mcp_manager.get_client(self.server_name) as client:
            arguments = {
                "channel_id": channel_id,
                "text": text
            }
            if thread_ts:
                arguments["thread_ts"] = thread_ts

            result = await client.call_tool("post_message", arguments)

            if result.get("isError"):
                raise Exception(f"MCP error: {result.get('content', 'Unknown error')}")

            return result.get("content", {})

    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user information via MCP"""
        async with await mcp_manager.get_client(self.server_name) as client:
            result = await client.call_tool("get_user", {
                "user_id": user_id
            })

            if result.get("isError"):
                raise Exception(f"MCP error: {result.get('content', 'Unknown error')}")

            return result.get("content", {})

    async def search_messages(
        self,
        query: str,
        count: int = 20
    ) -> List[Dict[str, Any]]:
        """Search messages across workspace via MCP"""
        async with await mcp_manager.get_client(self.server_name) as client:
            result = await client.call_tool("search_messages", {
                "query": query,
                "count": count
            })

            if result.get("isError"):
                raise Exception(f"MCP error: {result.get('content', 'Unknown error')}")

            return result.get("content", {}).get("messages", [])

    async def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Get channel information via MCP"""
        async with await mcp_manager.get_client(self.server_name) as client:
            result = await client.call_tool("get_channel_info", {
                "channel_id": channel_id
            })

            if result.get("isError"):
                raise Exception(f"MCP error: {result.get('content', 'Unknown error')}")

            return result.get("content", {})

    async def create_channel(
        self,
        name: str,
        is_private: bool = False
    ) -> Dict[str, Any]:
        """Create a new channel via MCP"""
        async with await mcp_manager.get_client(self.server_name) as client:
            result = await client.call_tool("create_channel", {
                "name": name,
                "is_private": is_private
            })

            if result.get("isError"):
                raise Exception(f"MCP error: {result.get('content', 'Unknown error')}")

            return result.get("content", {})

    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """List all available tools from the Slack MCP server"""
        async with await mcp_manager.get_client(self.server_name) as client:
            return await client.list_tools()