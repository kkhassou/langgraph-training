#!/usr/bin/env python3
"""
Jira MCP Server

This server provides tools for interacting with Jira API through MCP protocol.
"""
import asyncio
import os
import logging
from typing import Dict, Any, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
)

from jira import JIRA
from jira.exceptions import JIRAError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Jira client
JIRA_TOKEN = os.environ.get("JIRA_TOKEN")
JIRA_SERVER = os.environ.get("JIRA_SERVER")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL")

if not all([JIRA_TOKEN, JIRA_SERVER, JIRA_EMAIL]):
    raise ValueError("JIRA_TOKEN, JIRA_SERVER, and JIRA_EMAIL environment variables are required")

jira_client = JIRA(
    server=JIRA_SERVER,
    basic_auth=(JIRA_EMAIL, JIRA_TOKEN)
)

# Create MCP server instance
server = Server("jira-mcp-server")


@server.list_tools()
async def list_tools() -> ListToolsResult:
    """List available tools"""
    return ListToolsResult(
        tools=[
            Tool(
                name="list_projects",
                description="List all projects in the Jira instance",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="search_issues",
                description="Search for issues using JQL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "jql": {"type": "string", "description": "JQL query string"},
                        "max_results": {"type": "integer", "description": "Maximum number of results", "default": 50},
                    },
                    "required": ["jql"],
                },
            ),
            Tool(
                name="create_issue",
                description="Create a new issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_key": {"type": "string", "description": "Project key"},
                        "summary": {"type": "string", "description": "Issue summary"},
                        "description": {"type": "string", "description": "Issue description"},
                        "issue_type": {"type": "string", "description": "Issue type", "default": "Task"},
                        "assignee": {"type": "string", "description": "Assignee username"},
                        "priority": {"type": "string", "description": "Priority name"},
                        "labels": {"type": "array", "items": {"type": "string"}, "description": "Issue labels"},
                    },
                    "required": ["project_key", "summary", "description"],
                },
            ),
            Tool(
                name="get_issue",
                description="Get issue details",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {"type": "string", "description": "Issue key (e.g., PROJ-123)"},
                    },
                    "required": ["issue_key"],
                },
            ),
            Tool(
                name="update_issue",
                description="Update an existing issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {"type": "string", "description": "Issue key"},
                        "summary": {"type": "string", "description": "New summary"},
                        "description": {"type": "string", "description": "New description"},
                        "assignee": {"type": "string", "description": "New assignee username"},
                        "priority": {"type": "string", "description": "New priority name"},
                        "labels": {"type": "array", "items": {"type": "string"}, "description": "New labels"},
                    },
                    "required": ["issue_key"],
                },
            ),
            Tool(
                name="add_comment",
                description="Add a comment to an issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {"type": "string", "description": "Issue key"},
                        "comment": {"type": "string", "description": "Comment text"},
                    },
                    "required": ["issue_key", "comment"],
                },
            ),
            Tool(
                name="get_transitions",
                description="Get available transitions for an issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {"type": "string", "description": "Issue key"},
                    },
                    "required": ["issue_key"],
                },
            ),
            Tool(
                name="transition_issue",
                description="Transition an issue to a new status",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {"type": "string", "description": "Issue key"},
                        "transition_id": {"type": "string", "description": "Transition ID"},
                    },
                    "required": ["issue_key", "transition_id"],
                },
            ),
            Tool(
                name="get_user",
                description="Get user information",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID or username"},
                    },
                    "required": ["user_id"],
                },
            ),
        ]
    )


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls"""
    try:
        if name == "list_projects":
            return await handle_list_projects()
        elif name == "search_issues":
            return await handle_search_issues(arguments)
        elif name == "create_issue":
            return await handle_create_issue(arguments)
        elif name == "get_issue":
            return await handle_get_issue(arguments)
        elif name == "update_issue":
            return await handle_update_issue(arguments)
        elif name == "add_comment":
            return await handle_add_comment(arguments)
        elif name == "get_transitions":
            return await handle_get_transitions(arguments)
        elif name == "transition_issue":
            return await handle_transition_issue(arguments)
        elif name == "get_user":
            return await handle_get_user(arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True,
            )
    except Exception as e:
        logger.error(f"Error calling tool {name}: {str(e)}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def handle_list_projects() -> CallToolResult:
    """Handle list_projects tool"""
    try:
        projects = jira_client.projects()

        project_list = []
        for project in projects:
            project_list.append({
                "key": project.key,
                "name": project.name,
                "id": project.id,
                "description": getattr(project, "description", ""),
                "lead": getattr(project, "lead", {}).get("displayName", "") if hasattr(project, "lead") else "",
                "project_type": getattr(project, "projectTypeKey", ""),
            })

        result = {"projects": project_list}
        return CallToolResult(
            content=[TextContent(type="text", text=str(result))],
            isError=False,
        )

    except JIRAError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Jira API error: {str(e)}")],
            isError=True,
        )


async def handle_search_issues(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle search_issues tool"""
    try:
        jql = arguments["jql"]
        max_results = arguments.get("max_results", 50)

        issues = jira_client.search_issues(jql, maxResults=max_results)

        issue_list = []
        for issue in issues:
            issue_list.append({
                "key": issue.key,
                "summary": issue.fields.summary,
                "status": issue.fields.status.name,
                "assignee": issue.fields.assignee.displayName if issue.fields.assignee else None,
                "reporter": issue.fields.reporter.displayName if issue.fields.reporter else None,
                "priority": issue.fields.priority.name if issue.fields.priority else None,
                "created": str(issue.fields.created),
                "updated": str(issue.fields.updated),
                "description": issue.fields.description or "",
                "labels": getattr(issue.fields, "labels", []),
            })

        result = {"issues": issue_list}
        return CallToolResult(
            content=[TextContent(type="text", text=str(result))],
            isError=False,
        )

    except JIRAError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Jira API error: {str(e)}")],
            isError=True,
        )


async def handle_create_issue(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle create_issue tool"""
    try:
        project_key = arguments["project_key"]
        summary = arguments["summary"]
        description = arguments["description"]
        issue_type = arguments.get("issue_type", "Task")
        assignee = arguments.get("assignee")
        priority = arguments.get("priority")
        labels = arguments.get("labels", [])

        issue_dict = {
            'project': {'key': project_key},
            'summary': summary,
            'description': description,
            'issuetype': {'name': issue_type},
        }

        if assignee:
            issue_dict['assignee'] = {'name': assignee}
        if priority:
            issue_dict['priority'] = {'name': priority}
        if labels:
            issue_dict['labels'] = [{'name': label} for label in labels]

        new_issue = jira_client.create_issue(fields=issue_dict)

        result = {
            "key": new_issue.key,
            "id": new_issue.id,
            "url": f"{JIRA_SERVER}/browse/{new_issue.key}",
            "summary": summary,
            "status": "Open"  # Default status for new issues
        }

        return CallToolResult(
            content=[TextContent(type="text", text=str(result))],
            isError=False,
        )

    except JIRAError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Jira API error: {str(e)}")],
            isError=True,
        )


async def handle_get_issue(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle get_issue tool"""
    try:
        issue_key = arguments["issue_key"]

        issue = jira_client.issue(issue_key)

        result = {
            "key": issue.key,
            "summary": issue.fields.summary,
            "status": issue.fields.status.name,
            "assignee": issue.fields.assignee.displayName if issue.fields.assignee else None,
            "reporter": issue.fields.reporter.displayName if issue.fields.reporter else None,
            "priority": issue.fields.priority.name if issue.fields.priority else None,
            "created": str(issue.fields.created),
            "updated": str(issue.fields.updated),
            "description": issue.fields.description or "",
            "labels": getattr(issue.fields, "labels", []),
            "url": f"{JIRA_SERVER}/browse/{issue.key}"
        }

        return CallToolResult(
            content=[TextContent(type="text", text=str(result))],
            isError=False,
        )

    except JIRAError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Jira API error: {str(e)}")],
            isError=True,
        )


async def handle_update_issue(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle update_issue tool"""
    try:
        issue_key = arguments["issue_key"]

        issue = jira_client.issue(issue_key)
        update_fields = {}

        if "summary" in arguments:
            update_fields['summary'] = arguments['summary']
        if "description" in arguments:
            update_fields['description'] = arguments['description']
        if "assignee" in arguments:
            update_fields['assignee'] = {'name': arguments['assignee']}
        if "priority" in arguments:
            update_fields['priority'] = {'name': arguments['priority']}
        if "labels" in arguments:
            update_fields['labels'] = [{'name': label} for label in arguments['labels']]

        if update_fields:
            issue.update(fields=update_fields)

        result = {
            "key": issue.key,
            "updated": True,
            "url": f"{JIRA_SERVER}/browse/{issue.key}",
            "updated_fields": list(update_fields.keys())
        }

        return CallToolResult(
            content=[TextContent(type="text", text=str(result))],
            isError=False,
        )

    except JIRAError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Jira API error: {str(e)}")],
            isError=True,
        )


async def handle_add_comment(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle add_comment tool"""
    try:
        issue_key = arguments["issue_key"]
        comment_text = arguments["comment"]

        issue = jira_client.issue(issue_key)
        comment = jira_client.add_comment(issue, comment_text)

        result = {
            "comment_id": comment.id,
            "issue_key": issue_key,
            "comment": comment_text,
            "author": comment.author.displayName,
            "created": str(comment.created)
        }

        return CallToolResult(
            content=[TextContent(type="text", text=str(result))],
            isError=False,
        )

    except JIRAError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Jira API error: {str(e)}")],
            isError=True,
        )


async def handle_get_transitions(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle get_transitions tool"""
    try:
        issue_key = arguments["issue_key"]

        issue = jira_client.issue(issue_key)
        transitions = jira_client.transitions(issue)

        transition_list = []
        for transition in transitions:
            transition_list.append({
                "id": transition['id'],
                "name": transition['name'],
                "to_status": transition['to']['name']
            })

        result = {"transitions": transition_list}
        return CallToolResult(
            content=[TextContent(type="text", text=str(result))],
            isError=False,
        )

    except JIRAError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Jira API error: {str(e)}")],
            isError=True,
        )


async def handle_transition_issue(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle transition_issue tool"""
    try:
        issue_key = arguments["issue_key"]
        transition_id = arguments["transition_id"]

        issue = jira_client.issue(issue_key)
        jira_client.transition_issue(issue, transition_id)

        # Get updated issue to show new status
        updated_issue = jira_client.issue(issue_key)

        result = {
            "issue_key": issue_key,
            "transition_id": transition_id,
            "new_status": updated_issue.fields.status.name,
            "url": f"{JIRA_SERVER}/browse/{issue_key}"
        }

        return CallToolResult(
            content=[TextContent(type="text", text=str(result))],
            isError=False,
        )

    except JIRAError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Jira API error: {str(e)}")],
            isError=True,
        )


async def handle_get_user(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle get_user tool"""
    try:
        user_id = arguments["user_id"]

        user = jira_client.user(user_id)

        result = {
            "key": user.key,
            "name": user.name,
            "display_name": user.displayName,
            "email": getattr(user, "emailAddress", ""),
            "active": user.active,
            "timezone": getattr(user, "timeZone", ""),
        }

        return CallToolResult(
            content=[TextContent(type="text", text=str(result))],
            isError=False,
        )

    except JIRAError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Jira API error: {str(e)}")],
            isError=True,
        )


async def main():
    """Main entry point"""
    logger.info("Starting Jira MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())