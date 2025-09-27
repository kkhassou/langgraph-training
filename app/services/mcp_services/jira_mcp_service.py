from typing import List, Dict, Any, Optional
from app.services.mcp_services.mcp_client import mcp_manager
import logging

logger = logging.getLogger(__name__)


class JiraMCPService:
    """Service for Jira operations using MCP server"""

    def __init__(self):
        self.server_name = "jira"

    async def get_projects(self) -> List[Dict[str, Any]]:
        """Get list of projects via MCP"""
        async with await mcp_manager.get_client(self.server_name) as client:
            result = await client.call_tool("list_projects", {})

            if result.get("isError"):
                raise Exception(f"MCP error: {result.get('content', 'Unknown error')}")

            return result.get("content", {}).get("projects", [])

    async def search_issues(
        self,
        jql: str,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Search issues using JQL via MCP"""
        async with await mcp_manager.get_client(self.server_name) as client:
            result = await client.call_tool("search_issues", {
                "jql": jql,
                "max_results": max_results
            })

            if result.get("isError"):
                raise Exception(f"MCP error: {result.get('content', 'Unknown error')}")

            return result.get("content", {}).get("issues", [])

    async def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Task",
        assignee: Optional[str] = None,
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a new issue via MCP"""
        async with await mcp_manager.get_client(self.server_name) as client:
            arguments = {
                "project_key": project_key,
                "summary": summary,
                "description": description,
                "issue_type": issue_type
            }

            if assignee:
                arguments["assignee"] = assignee
            if priority:
                arguments["priority"] = priority
            if labels:
                arguments["labels"] = labels

            result = await client.call_tool("create_issue", arguments)

            if result.get("isError"):
                raise Exception(f"MCP error: {result.get('content', 'Unknown error')}")

            return result.get("content", {})

    async def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """Get issue details via MCP"""
        async with await mcp_manager.get_client(self.server_name) as client:
            result = await client.call_tool("get_issue", {
                "issue_key": issue_key
            })

            if result.get("isError"):
                raise Exception(f"MCP error: {result.get('content', 'Unknown error')}")

            return result.get("content", {})

    async def update_issue(
        self,
        issue_key: str,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        assignee: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Update an existing issue via MCP"""
        async with await mcp_manager.get_client(self.server_name) as client:
            arguments = {"issue_key": issue_key}

            if summary:
                arguments["summary"] = summary
            if description:
                arguments["description"] = description
            if assignee:
                arguments["assignee"] = assignee
            if status:
                arguments["status"] = status
            if priority:
                arguments["priority"] = priority
            if labels:
                arguments["labels"] = labels

            result = await client.call_tool("update_issue", arguments)

            if result.get("isError"):
                raise Exception(f"MCP error: {result.get('content', 'Unknown error')}")

            return result.get("content", {})

    async def add_comment(
        self,
        issue_key: str,
        comment: str
    ) -> Dict[str, Any]:
        """Add a comment to an issue via MCP"""
        async with await mcp_manager.get_client(self.server_name) as client:
            result = await client.call_tool("add_comment", {
                "issue_key": issue_key,
                "comment": comment
            })

            if result.get("isError"):
                raise Exception(f"MCP error: {result.get('content', 'Unknown error')}")

            return result.get("content", {})

    async def get_issue_transitions(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get available transitions for an issue via MCP"""
        async with await mcp_manager.get_client(self.server_name) as client:
            result = await client.call_tool("get_transitions", {
                "issue_key": issue_key
            })

            if result.get("isError"):
                raise Exception(f"MCP error: {result.get('content', 'Unknown error')}")

            return result.get("content", {}).get("transitions", [])

    async def transition_issue(
        self,
        issue_key: str,
        transition_id: str
    ) -> Dict[str, Any]:
        """Transition an issue to a new status via MCP"""
        async with await mcp_manager.get_client(self.server_name) as client:
            result = await client.call_tool("transition_issue", {
                "issue_key": issue_key,
                "transition_id": transition_id
            })

            if result.get("isError"):
                raise Exception(f"MCP error: {result.get('content', 'Unknown error')}")

            return result.get("content", {})

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get user information via MCP"""
        async with await mcp_manager.get_client(self.server_name) as client:
            result = await client.call_tool("get_user", {
                "user_id": user_id
            })

            if result.get("isError"):
                raise Exception(f"MCP error: {result.get('content', 'Unknown error')}")

            return result.get("content", {})

    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """List all available tools from the Jira MCP server"""
        async with await mcp_manager.get_client(self.server_name) as client:
            return await client.list_tools()