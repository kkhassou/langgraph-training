"""GitHub MCP Node - Handles GitHub operations via MCP server"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import logging

from src.services.mcp.github import GitHubMCPService
from src.nodes.base import BaseNode, NodeResult

logger = logging.getLogger(__name__)


class GitHubMCPInput(BaseModel):
    """Input schema for GitHub MCP node"""
    action: str = Field(..., description="Action to perform: get_repository, list_issues, create_issue, get_file, create_pull_request, list_pull_requests, search_repositories")

    # Common parameters
    repo: Optional[str] = Field(None, description="Repository name (owner/repo)")

    # For list_issues and list_pull_requests
    state: Optional[str] = Field("open", description="State: open, closed, all")
    limit: Optional[int] = Field(10, description="Max number of results")

    # For create_issue
    title: Optional[str] = Field(None, description="Issue/PR title")
    body: Optional[str] = Field(None, description="Issue/PR body")
    labels: Optional[List[str]] = Field(None, description="Issue labels")

    # For get_file
    path: Optional[str] = Field(None, description="File path in repository")
    branch: Optional[str] = Field("main", description="Branch name")

    # For create_pull_request
    head: Optional[str] = Field(None, description="Head branch")
    base: Optional[str] = Field("main", description="Base branch")

    # For search
    query: Optional[str] = Field(None, description="Search query")


class GitHubMCPNode(BaseNode):
    """Node for GitHub operations via MCP server"""

    def __init__(self):
        super().__init__("github-mcp")
        self.github_service = GitHubMCPService()

    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """Execute GitHub MCP node"""
        try:
            action = input_data.get("action")

            if action == "get_repository":
                repo = input_data.get("repo")
                if not repo:
                    raise ValueError("repo is required for get_repository action")

                result = await self.github_service.get_repository(repo)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "get_repository", "repo": repo}
                )

            elif action == "list_issues":
                repo = input_data.get("repo")
                state = input_data.get("state", "open")
                limit = input_data.get("limit", 10)

                if not repo:
                    raise ValueError("repo is required for list_issues action")

                result = await self.github_service.list_issues(repo, state, limit)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "list_issues", "repo": repo}
                )

            elif action == "create_issue":
                repo = input_data.get("repo")
                title = input_data.get("title")
                body = input_data.get("body")
                labels = input_data.get("labels")

                if not repo or not title:
                    raise ValueError("repo and title are required for create_issue action")

                result = await self.github_service.create_issue(repo, title, body, labels)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "create_issue", "repo": repo}
                )

            elif action == "get_file":
                repo = input_data.get("repo")
                path = input_data.get("path")
                branch = input_data.get("branch", "main")

                if not repo or not path:
                    raise ValueError("repo and path are required for get_file action")

                result = await self.github_service.get_file(repo, path, branch)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "get_file", "repo": repo, "path": path}
                )

            elif action == "create_pull_request":
                repo = input_data.get("repo")
                title = input_data.get("title")
                head = input_data.get("head")
                base = input_data.get("base", "main")
                body = input_data.get("body")

                if not repo or not title or not head:
                    raise ValueError("repo, title, and head are required for create_pull_request action")

                result = await self.github_service.create_pull_request(repo, title, head, base, body)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "create_pull_request", "repo": repo}
                )

            elif action == "list_pull_requests":
                repo = input_data.get("repo")
                state = input_data.get("state", "open")
                limit = input_data.get("limit", 10)

                if not repo:
                    raise ValueError("repo is required for list_pull_requests action")

                result = await self.github_service.list_pull_requests(repo, state, limit)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "list_pull_requests", "repo": repo}
                )

            elif action == "search_repositories":
                query = input_data.get("query")
                limit = input_data.get("limit", 10)

                if not query:
                    raise ValueError("query is required for search_repositories action")

                result = await self.github_service.search_repositories(query, limit)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "search_repositories", "query": query}
                )

            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Error in GitHub MCP node: {e}")
            return NodeResult(
                success=False,
                error=str(e),
                metadata={"action": input_data.get("action")}
            )

    async def cleanup(self):
        """Cleanup GitHub MCP resources"""
        try:
            await self.github_service.disconnect()
        except Exception as e:
            logger.error(f"Error during GitHub MCP cleanup: {e}")


# Create node instance
github_mcp_node = GitHubMCPNode()


async def github_mcp_node_handler(input_data: GitHubMCPInput) -> Dict[str, Any]:
    """Handler function for GitHub MCP node endpoint"""
    result = await github_mcp_node.execute(input_data.model_dump())
    return result.model_dump()
