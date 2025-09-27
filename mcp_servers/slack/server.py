#!/usr/bin/env python3
"""
Slack MCP Server

This server provides tools for interacting with Slack API through MCP protocol.
"""
import asyncio
import os
import logging
from datetime import datetime, timedelta
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

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Slack client
SLACK_TOKEN = os.environ.get("SLACK_TOKEN")
if not SLACK_TOKEN:
    raise ValueError("SLACK_TOKEN environment variable is required")

slack_client = AsyncWebClient(token=SLACK_TOKEN)

# Create MCP server instance
server = Server("slack-mcp-server")


@server.list_tools()
async def list_tools() -> ListToolsResult:
    """List available tools"""
    return ListToolsResult(
        tools=[
            Tool(
                name="list_channels",
                description="List all channels in the workspace",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="get_messages",
                description="Get messages from a specific channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {"type": "string", "description": "Channel ID"},
                        "limit": {"type": "integer", "description": "Number of messages to fetch", "default": 100},
                        "days_back": {"type": "integer", "description": "How many days back to fetch", "default": 7},
                    },
                    "required": ["channel_id"],
                },
            ),
            Tool(
                name="post_message",
                description="Post a message to a channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {"type": "string", "description": "Channel ID"},
                        "text": {"type": "string", "description": "Message text"},
                        "thread_ts": {"type": "string", "description": "Thread timestamp for reply"},
                    },
                    "required": ["channel_id", "text"],
                },
            ),
            Tool(
                name="get_user",
                description="Get user information",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID"},
                    },
                    "required": ["user_id"],
                },
            ),
            Tool(
                name="search_messages",
                description="Search messages across the workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "count": {"type": "integer", "description": "Number of results", "default": 20},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="get_channel_info",
                description="Get information about a specific channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {"type": "string", "description": "Channel ID"},
                    },
                    "required": ["channel_id"],
                },
            ),
            Tool(
                name="create_channel",
                description="Create a new channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Channel name"},
                        "is_private": {"type": "boolean", "description": "Whether the channel is private", "default": False},
                    },
                    "required": ["name"],
                },
            ),
        ]
    )


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls"""
    try:
        if name == "list_channels":
            return await handle_list_channels()
        elif name == "get_messages":
            return await handle_get_messages(arguments)
        elif name == "post_message":
            return await handle_post_message(arguments)
        elif name == "get_user":
            return await handle_get_user(arguments)
        elif name == "search_messages":
            return await handle_search_messages(arguments)
        elif name == "get_channel_info":
            return await handle_get_channel_info(arguments)
        elif name == "create_channel":
            return await handle_create_channel(arguments)
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


async def handle_list_channels() -> CallToolResult:
    """Handle list_channels tool"""
    try:
        response = await slack_client.conversations_list(
            types="public_channel,private_channel"
        )

        channels = []
        for channel in response["channels"]:
            channels.append({
                "id": channel["id"],
                "name": channel["name"],
                "is_private": channel.get("is_private", False),
                "num_members": channel.get("num_members", 0),
                "purpose": channel.get("purpose", {}).get("value", ""),
                "topic": channel.get("topic", {}).get("value", ""),
            })

        result = {"channels": channels}
        return CallToolResult(
            content=[TextContent(type="text", text=str(result))],
            isError=False,
        )

    except SlackApiError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Slack API error: {e.response['error']}")],
            isError=True,
        )


async def handle_get_messages(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle get_messages tool"""
    try:
        channel_id = arguments["channel_id"]
        limit = arguments.get("limit", 100)
        days_back = arguments.get("days_back", 7)

        # Calculate timestamp
        oldest_timestamp = (datetime.now() - timedelta(days=days_back)).timestamp()

        response = await slack_client.conversations_history(
            channel=channel_id,
            limit=limit,
            oldest=oldest_timestamp
        )

        messages = []
        for message in response["messages"]:
            if message.get("subtype") in ["bot_message", "channel_join", "channel_leave"]:
                continue

            messages.append({
                "text": message.get("text", ""),
                "user": message.get("user", "unknown"),
                "timestamp": message.get("ts", ""),
                "thread_ts": message.get("thread_ts"),
                "reactions": message.get("reactions", []),
            })

        result = {"messages": messages}
        return CallToolResult(
            content=[TextContent(type="text", text=str(result))],
            isError=False,
        )

    except SlackApiError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Slack API error: {e.response['error']}")],
            isError=True,
        )


async def handle_post_message(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle post_message tool"""
    try:
        channel_id = arguments["channel_id"]
        text = arguments["text"]
        thread_ts = arguments.get("thread_ts")

        response = await slack_client.chat_postMessage(
            channel=channel_id,
            text=text,
            thread_ts=thread_ts
        )

        result = {
            "ts": response["ts"],
            "channel": response["channel"],
            "text": text,
        }

        return CallToolResult(
            content=[TextContent(type="text", text=str(result))],
            isError=False,
        )

    except SlackApiError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Slack API error: {e.response['error']}")],
            isError=True,
        )


async def handle_get_user(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle get_user tool"""
    try:
        user_id = arguments["user_id"]

        response = await slack_client.users_info(user=user_id)
        user = response["user"]

        result = {
            "id": user["id"],
            "name": user.get("name", ""),
            "real_name": user.get("real_name", ""),
            "display_name": user.get("profile", {}).get("display_name", ""),
            "email": user.get("profile", {}).get("email", ""),
            "is_bot": user.get("is_bot", False),
        }

        return CallToolResult(
            content=[TextContent(type="text", text=str(result))],
            isError=False,
        )

    except SlackApiError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Slack API error: {e.response['error']}")],
            isError=True,
        )


async def handle_search_messages(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle search_messages tool"""
    try:
        query = arguments["query"]
        count = arguments.get("count", 20)

        response = await slack_client.search_messages(
            query=query,
            count=count
        )

        messages = []
        for match in response["messages"]["matches"]:
            messages.append({
                "text": match.get("text", ""),
                "user": match.get("user", "unknown"),
                "channel": match.get("channel", {}).get("id", ""),
                "timestamp": match.get("ts", ""),
                "score": match.get("score", 0),
            })

        result = {"messages": messages}
        return CallToolResult(
            content=[TextContent(type="text", text=str(result))],
            isError=False,
        )

    except SlackApiError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Slack API error: {e.response['error']}")],
            isError=True,
        )


async def handle_get_channel_info(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle get_channel_info tool"""
    try:
        channel_id = arguments["channel_id"]

        response = await slack_client.conversations_info(channel=channel_id)
        channel = response["channel"]

        result = {
            "id": channel["id"],
            "name": channel["name"],
            "is_private": channel.get("is_private", False),
            "num_members": channel.get("num_members", 0),
            "purpose": channel.get("purpose", {}).get("value", ""),
            "topic": channel.get("topic", {}).get("value", ""),
            "created": channel.get("created", ""),
            "creator": channel.get("creator", ""),
        }

        return CallToolResult(
            content=[TextContent(type="text", text=str(result))],
            isError=False,
        )

    except SlackApiError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Slack API error: {e.response['error']}")],
            isError=True,
        )


async def handle_create_channel(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle create_channel tool"""
    try:
        name = arguments["name"]
        is_private = arguments.get("is_private", False)

        response = await slack_client.conversations_create(
            name=name,
            is_private=is_private
        )

        channel = response["channel"]
        result = {
            "id": channel["id"],
            "name": channel["name"],
            "is_private": channel.get("is_private", False),
            "created": channel.get("created", ""),
        }

        return CallToolResult(
            content=[TextContent(type="text", text=str(result))],
            isError=False,
        )

    except SlackApiError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Slack API error: {e.response['error']}")],
            isError=True,
        )


async def main():
    """Main entry point"""
    logger.info("Starting Slack MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())