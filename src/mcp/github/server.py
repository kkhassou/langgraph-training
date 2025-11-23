"""GitHub MCP Server - Provides tools to interact with GitHub API

This server exposes tools for:
- Repository operations
- Issue management
- Pull request operations
- File operations
- Search functionality
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

# Import MCP SDK
try:
    from mcp.server.models import InitializationOptions
    import mcp.types as types
    from mcp.server import NotificationOptions, Server
    import mcp.server.stdio
    MCP_AVAILABLE = True
    logger.info("MCP SDK imported successfully")
except ImportError as e:
    logger.error(f"Failed to import MCP SDK: {e}")
    MCP_AVAILABLE = False
    sys.exit(1)

# Import GitHub SDK
try:
    from github import Github, GithubException
    GITHUB_AVAILABLE = True
    logger.info("GitHub client imported successfully")
except ImportError as e:
    logger.error(f"Failed to import GitHub client: {e}")
    GITHUB_AVAILABLE = False
    sys.exit(1)

# Global GitHub client
github_client = None

async def init_github_client():
    """Initialize GitHub client"""
    global github_client

    try:
        # Get GitHub token from environment
        github_token = os.getenv("GITHUB_TOKEN")

        if not github_token:
            raise ValueError("GITHUB_TOKEN environment variable not found")

        logger.info("Initializing GitHub client...")
        github_client = Github(github_token)

        # Test authentication
        user = github_client.get_user()
        logger.info(f"GitHub client initialized successfully. Authenticated as: {user.login}")

    except Exception as e:
        logger.error(f"Failed to initialize GitHub client: {e}")
        raise

# Create MCP server instance
server = Server("github-mcp")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available GitHub tools"""
    return [
        types.Tool(
            name="get_repository",
            description="Get repository information",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name (owner/repo)"
                    }
                },
                "required": ["repo"]
            }
        ),
        types.Tool(
            name="list_issues",
            description="List repository issues",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name (owner/repo)"
                    },
                    "state": {
                        "type": "string",
                        "description": "Issue state: open, closed, all (default: open)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max number of issues to return (default: 10)"
                    }
                },
                "required": ["repo"]
            }
        ),
        types.Tool(
            name="create_issue",
            description="Create a new issue",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name (owner/repo)"
                    },
                    "title": {
                        "type": "string",
                        "description": "Issue title"
                    },
                    "body": {
                        "type": "string",
                        "description": "Issue body"
                    },
                    "labels": {
                        "type": "array",
                        "description": "Issue labels (optional)",
                        "items": {"type": "string"}
                    }
                },
                "required": ["repo", "title"]
            }
        ),
        types.Tool(
            name="get_file",
            description="Get file content from repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name (owner/repo)"
                    },
                    "path": {
                        "type": "string",
                        "description": "File path in repository"
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name (default: main)"
                    }
                },
                "required": ["repo", "path"]
            }
        ),
        types.Tool(
            name="create_pull_request",
            description="Create a pull request",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name (owner/repo)"
                    },
                    "title": {
                        "type": "string",
                        "description": "PR title"
                    },
                    "body": {
                        "type": "string",
                        "description": "PR description"
                    },
                    "head": {
                        "type": "string",
                        "description": "Head branch"
                    },
                    "base": {
                        "type": "string",
                        "description": "Base branch (default: main)"
                    }
                },
                "required": ["repo", "title", "head"]
            }
        ),
        types.Tool(
            name="list_pull_requests",
            description="List repository pull requests",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name (owner/repo)"
                    },
                    "state": {
                        "type": "string",
                        "description": "PR state: open, closed, all (default: open)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max number of PRs to return (default: 10)"
                    }
                },
                "required": ["repo"]
            }
        ),
        types.Tool(
            name="search_repositories",
            description="Search GitHub repositories",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max number of results (default: 10)"
                    }
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests"""

    if not github_client:
        await init_github_client()

    try:
        if name == "get_repository":
            return await get_repository_tool(arguments or {})
        elif name == "list_issues":
            return await list_issues_tool(arguments or {})
        elif name == "create_issue":
            return await create_issue_tool(arguments or {})
        elif name == "get_file":
            return await get_file_tool(arguments or {})
        elif name == "create_pull_request":
            return await create_pull_request_tool(arguments or {})
        elif name == "list_pull_requests":
            return await list_pull_requests_tool(arguments or {})
        elif name == "search_repositories":
            return await search_repositories_tool(arguments or {})
        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

async def get_repository_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Get repository information"""
    repo_name = arguments.get("repo")

    if not repo_name:
        return [types.TextContent(type="text", text="Error: repo is required")]

    try:
        repo = github_client.get_repo(repo_name)

        response_text = f"Repository: {repo.full_name}\n"
        response_text += f"Description: {repo.description or 'No description'}\n"
        response_text += f"Stars: {repo.stargazers_count}\n"
        response_text += f"Forks: {repo.forks_count}\n"
        response_text += f"Open Issues: {repo.open_issues_count}\n"
        response_text += f"Language: {repo.language or 'Unknown'}\n"
        response_text += f"URL: {repo.html_url}\n"
        response_text += f"Created: {repo.created_at}\n"
        response_text += f"Updated: {repo.updated_at}"

        return [types.TextContent(type="text", text=response_text)]

    except GithubException as error:
        logger.error(f"Error getting repository: {error}")
        return [types.TextContent(type="text", text=f"Error getting repository: {error}")]

async def list_issues_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """List repository issues"""
    repo_name = arguments.get("repo")
    state = arguments.get("state", "open")
    limit = arguments.get("limit", 10)

    if not repo_name:
        return [types.TextContent(type="text", text="Error: repo is required")]

    try:
        repo = github_client.get_repo(repo_name)
        issues = repo.get_issues(state=state)

        response_text = f"Issues in {repo_name} ({state}):\n\n"

        count = 0
        for issue in issues:
            if count >= limit:
                break

            response_text += f"#{issue.number} {issue.title}\n"
            response_text += f"  State: {issue.state}\n"
            response_text += f"  Author: {issue.user.login}\n"
            response_text += f"  Created: {issue.created_at}\n"
            response_text += f"  URL: {issue.html_url}\n\n"
            count += 1

        if count == 0:
            response_text += "No issues found."

        return [types.TextContent(type="text", text=response_text)]

    except GithubException as error:
        logger.error(f"Error listing issues: {error}")
        return [types.TextContent(type="text", text=f"Error listing issues: {error}")]

async def create_issue_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Create a new issue"""
    repo_name = arguments.get("repo")
    title = arguments.get("title")
    body = arguments.get("body", "")
    labels = arguments.get("labels", [])

    if not repo_name or not title:
        return [types.TextContent(type="text", text="Error: repo and title are required")]

    try:
        repo = github_client.get_repo(repo_name)
        issue = repo.create_issue(title=title, body=body, labels=labels)

        response_text = f"Issue created successfully!\n"
        response_text += f"Issue #{issue.number}: {issue.title}\n"
        response_text += f"URL: {issue.html_url}"

        return [types.TextContent(type="text", text=response_text)]

    except GithubException as error:
        logger.error(f"Error creating issue: {error}")
        return [types.TextContent(type="text", text=f"Error creating issue: {error}")]

async def get_file_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Get file content from repository"""
    repo_name = arguments.get("repo")
    path = arguments.get("path")
    branch = arguments.get("branch", "main")

    if not repo_name or not path:
        return [types.TextContent(type="text", text="Error: repo and path are required")]

    try:
        repo = github_client.get_repo(repo_name)
        file_content = repo.get_contents(path, ref=branch)

        if isinstance(file_content, list):
            return [types.TextContent(type="text", text="Error: Path is a directory, not a file")]

        content = file_content.decoded_content.decode('utf-8')

        response_text = f"File: {path}\n"
        response_text += f"Branch: {branch}\n"
        response_text += f"Size: {file_content.size} bytes\n"
        response_text += f"SHA: {file_content.sha}\n\n"
        response_text += "Content:\n"
        response_text += "```\n"
        response_text += content[:2000]  # Limit to first 2000 chars
        if len(content) > 2000:
            response_text += "\n... (truncated)"
        response_text += "\n```"

        return [types.TextContent(type="text", text=response_text)]

    except GithubException as error:
        logger.error(f"Error getting file: {error}")
        return [types.TextContent(type="text", text=f"Error getting file: {error}")]

async def create_pull_request_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Create a pull request"""
    repo_name = arguments.get("repo")
    title = arguments.get("title")
    body = arguments.get("body", "")
    head = arguments.get("head")
    base = arguments.get("base", "main")

    if not repo_name or not title or not head:
        return [types.TextContent(type="text", text="Error: repo, title, and head are required")]

    try:
        repo = github_client.get_repo(repo_name)
        pr = repo.create_pull(title=title, body=body, head=head, base=base)

        response_text = f"Pull request created successfully!\n"
        response_text += f"PR #{pr.number}: {pr.title}\n"
        response_text += f"From: {head} → To: {base}\n"
        response_text += f"URL: {pr.html_url}"

        return [types.TextContent(type="text", text=response_text)]

    except GithubException as error:
        logger.error(f"Error creating pull request: {error}")
        return [types.TextContent(type="text", text=f"Error creating pull request: {error}")]

async def list_pull_requests_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """List repository pull requests"""
    repo_name = arguments.get("repo")
    state = arguments.get("state", "open")
    limit = arguments.get("limit", 10)

    if not repo_name:
        return [types.TextContent(type="text", text="Error: repo is required")]

    try:
        repo = github_client.get_repo(repo_name)
        pulls = repo.get_pulls(state=state)

        response_text = f"Pull requests in {repo_name} ({state}):\n\n"

        count = 0
        for pr in pulls:
            if count >= limit:
                break

            response_text += f"#{pr.number} {pr.title}\n"
            response_text += f"  State: {pr.state}\n"
            response_text += f"  Author: {pr.user.login}\n"
            response_text += f"  From: {pr.head.ref} → To: {pr.base.ref}\n"
            response_text += f"  Created: {pr.created_at}\n"
            response_text += f"  URL: {pr.html_url}\n\n"
            count += 1

        if count == 0:
            response_text += "No pull requests found."

        return [types.TextContent(type="text", text=response_text)]

    except GithubException as error:
        logger.error(f"Error listing pull requests: {error}")
        return [types.TextContent(type="text", text=f"Error listing pull requests: {error}")]

async def search_repositories_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Search GitHub repositories"""
    query = arguments.get("query")
    limit = arguments.get("limit", 10)

    if not query:
        return [types.TextContent(type="text", text="Error: query is required")]

    try:
        repositories = github_client.search_repositories(query=query)

        response_text = f"Search results for '{query}':\n\n"

        count = 0
        for repo in repositories:
            if count >= limit:
                break

            response_text += f"{count + 1}. {repo.full_name}\n"
            response_text += f"   {repo.description or 'No description'}\n"
            response_text += f"   Stars: {repo.stargazers_count} | Language: {repo.language or 'Unknown'}\n"
            response_text += f"   URL: {repo.html_url}\n\n"
            count += 1

        if count == 0:
            response_text += "No repositories found."

        return [types.TextContent(type="text", text=response_text)]

    except GithubException as error:
        logger.error(f"Error searching repositories: {error}")
        return [types.TextContent(type="text", text=f"Error searching repositories: {error}")]

async def main():
    """Main entry point for the MCP server"""
    logger.info("Starting GitHub MCP server...")

    # Initialize GitHub client
    try:
        await init_github_client()
    except Exception as e:
        logger.error(f"Failed to initialize GitHub client: {e}")
        sys.exit(1)

    # Run the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Server running on stdio")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="github-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
