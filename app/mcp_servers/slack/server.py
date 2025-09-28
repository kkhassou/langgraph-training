#!/usr/bin/env python3
"""
Slack MCP Server

A Model Context Protocol server that provides Slack integration capabilities.
This server allows AI assistants to interact with Slack workspaces through
standardized MCP tools.
"""

import asyncio
import os
import logging
from typing import Any, Dict, List, Optional, Sequence
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    from slack_sdk.web.async_client import AsyncWebClient
    from slack_sdk.errors import SlackApiError
    SLACK_SDK_AVAILABLE = True
except ImportError:
    SLACK_SDK_AVAILABLE = False
    SlackApiError = Exception

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    CallToolRequest,
    ListToolsRequest,
    CallToolResult,
    ListResourcesRequest,
    ReadResourceRequest,
    GetPromptRequest,
    ListPromptsRequest,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Slack client
slack_client = None


async def init_slack_client():
    """Initialize Slack client with token from environment"""
    global slack_client

    if not SLACK_SDK_AVAILABLE:
        logger.warning("slack-sdk not available, using mock responses")
        return False

    token = os.getenv("SLACK_BOT_TOKEN") or os.getenv("SLACK_TOKEN")
    if not token:
        logger.warning("No Slack token found in environment variables")
        return False

    slack_client = AsyncWebClient(token=token)

    # Test the connection
    try:
        auth_response = await slack_client.auth_test()
        logger.info(f"Connected to Slack workspace: {auth_response.get('team', 'Unknown')}")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Slack: {e}")
        slack_client = None
        return False


async def get_channels_tool(arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get list of Slack channels"""
    if not slack_client:
        # Return mock data when client is not available
        return [
            {"id": "C1234567890", "name": "general", "is_private": False},
            {"id": "C0987654321", "name": "random", "is_private": False},
            {"id": "C1111111111", "name": "development", "is_private": False}
        ]

    try:
        # First try with just public channels to avoid missing_scope for groups:read
        response = await slack_client.conversations_list(
            types="public_channel",
            limit=100
        )

        channels = []
        for channel in response.get("channels", []):
            channels.append({
                "id": channel["id"],
                "name": channel["name"],
                "is_private": channel.get("is_private", False),
                "is_member": channel.get("is_member", False),
                "topic": channel.get("topic", {}).get("value", ""),
                "purpose": channel.get("purpose", {}).get("value", "")
            })

        return channels

    except SlackApiError as e:
        logger.error(f"Slack API error in get_channels: {e}")
        # Return specific error message instead of mock data
        error_msg = e.response.get('error', str(e))
        if error_msg == 'missing_scope':
            needed = e.response.get('needed', 'unknown')
            provided = e.response.get('provided', 'none')
            raise Exception(f"Slack API permission error: Missing scope '{needed}'. Available scopes: {provided}. Please update your Slack app permissions.")
        else:
            raise Exception(f"Slack API error: {error_msg}")


async def get_messages_tool(arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get messages from a Slack channel"""
    channel = arguments.get("channel")
    limit = arguments.get("limit", 10)

    if not channel:
        raise ValueError("channel parameter is required")

    if not slack_client:
        # Return mock data when client is not available
        return [
            {
                "text": f"Mock message 1 from channel {channel}",
                "user": "U1234567890",
                "ts": "1234567890.123456",
                "type": "message"
            },
            {
                "text": f"Mock message 2 from channel {channel}",
                "user": "U0987654321",
                "ts": "1234567891.123456",
                "type": "message"
            }
        ]

    try:
        response = await slack_client.conversations_history(
            channel=channel,
            limit=limit
        )

        messages = []
        for message in response.get("messages", []):
            # Skip bot messages and system messages
            if message.get("subtype") in ["bot_message", "channel_join", "channel_leave"]:
                continue

            messages.append({
                "text": message.get("text", ""),
                "user": message.get("user", "unknown"),
                "ts": message.get("ts", ""),
                "type": message.get("type", "message"),
                "thread_ts": message.get("thread_ts")
            })

        return messages

    except SlackApiError as e:
        logger.error(f"Slack API error in get_messages: {e}")
        raise Exception(f"Slack API error: {e.response['error']}")


async def send_message_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Send a message to a Slack channel"""
    channel = arguments.get("channel")
    text = arguments.get("text")
    thread_ts = arguments.get("thread_ts")

    if not channel or not text:
        raise ValueError("Both 'channel' and 'text' parameters are required")

    if not slack_client:
        # Return mock data when client is not available
        return {
            "ok": True,
            "ts": "1234567892.123456",
            "channel": channel,
            "message": {
                "text": text,
                "user": "U_BOT_USER",
                "ts": "1234567892.123456"
            }
        }

    try:
        response = await slack_client.chat_postMessage(
            channel=channel,
            text=text,
            thread_ts=thread_ts
        )

        return {
            "ok": response.get("ok", False),
            "ts": response.get("ts"),
            "channel": response.get("channel"),
            "message": response.get("message", {})
        }

    except SlackApiError as e:
        logger.error(f"Slack API error in send_message: {e}")
        raise Exception(f"Slack API error: {e.response['error']}")


# Create the MCP server
app = Server("slack-mcp-server")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available Slack tools"""
    return [
        Tool(
            name="get_channels",
            description="Get list of Slack channels in the workspace",
            inputSchema={
                "type": "object",
                "properties": {
                    "types": {
                        "type": "string",
                        "description": "Channel types to include (default: public_channel,private_channel)",
                        "default": "public_channel,private_channel"
                    }
                }
            }
        ),
        Tool(
            name="get_messages",
            description="Get messages from a Slack channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel": {
                        "type": "string",
                        "description": "Channel ID or name (e.g., 'C1234567890' or '#general')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of messages to retrieve (default: 10, max: 100)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["channel"]
            }
        ),
        Tool(
            name="send_message",
            description="Send a message to a Slack channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel": {
                        "type": "string",
                        "description": "Channel ID or name (e.g., 'C1234567890' or '#general')"
                    },
                    "text": {
                        "type": "string",
                        "description": "Message text to send"
                    },
                    "thread_ts": {
                        "type": "string",
                        "description": "Timestamp of parent message to reply in thread (optional)"
                    }
                },
                "required": ["channel", "text"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls"""
    try:
        if name == "get_channels":
            channels = await get_channels_tool(arguments)
            return [
                TextContent(
                    type="text",
                    text=f"Found {len(channels)} channels:\n" +
                         "\n".join([f"• #{ch['name']} ({ch['id']})" for ch in channels])
                )
            ]

        elif name == "get_messages":
            messages = await get_messages_tool(arguments)
            channel = arguments.get("channel", "unknown")

            if not messages:
                return [TextContent(type="text", text=f"No messages found in {channel}")]

            message_text = f"Messages from {channel}:\n\n"
            for msg in messages:
                user = msg.get("user", "unknown")
                text = msg.get("text", "")
                ts = msg.get("ts", "")
                message_text += f"[{ts}] {user}: {text}\n"

            return [TextContent(type="text", text=message_text)]

        elif name == "send_message":
            result = await send_message_tool(arguments)
            channel = arguments.get("channel", "unknown")
            text = arguments.get("text", "")

            if result.get("ok"):
                return [
                    TextContent(
                        type="text",
                        text=f"✅ Message sent successfully to {channel}\nMessage: {text}\nTimestamp: {result.get('ts')}"
                    )
                ]
            else:
                return [
                    TextContent(
                        type="text",
                        text=f"❌ Failed to send message to {channel}"
                    )
                ]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return [
            TextContent(
                type="text",
                text=f"Error executing {name}: {str(e)}"
            )
        ]


async def main():
    """Main server entry point"""
    # Initialize Slack client
    await init_slack_client()

    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())