"""Google Keep MCP Server - Provides tools to interact with Google Keep API

This server exposes tools for:
- Creating notes
- Reading notes
- Updating notes
- Deleting notes
- Listing notes
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

# Import Google API client
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
    logger.info("Google API client imported successfully")
except ImportError as e:
    logger.error(f"Failed to import Google API client: {e}")
    GOOGLE_API_AVAILABLE = False
    sys.exit(1)

# Google Keep API scopes
SCOPES = [
    'https://www.googleapis.com/auth/keep',
    'https://www.googleapis.com/auth/keep.readonly'
]

# Global Keep service
keep_service = None

async def init_keep_client():
    """Initialize Google Keep API client"""
    global keep_service

    try:
        # Get token and credentials paths from environment
        token_path = os.getenv(
            "GOOGLE_TOKEN_PATH",
            os.getenv("KEEP_TOKEN_PATH", "secrets/google_token.json")
        )
        credentials_path = os.getenv(
            "GOOGLE_CREDENTIALS_PATH",
            os.getenv("KEEP_CREDENTIALS_PATH", "secrets/google_credentials.json")
        )

        logger.info(f"Loading credentials from: {credentials_path}")
        logger.info(f"Loading token from: {token_path}")

        if not os.path.exists(token_path):
            raise FileNotFoundError(f"Token file not found: {token_path}")

        # Load credentials from token
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            logger.info("Token expired, refreshing...")
            creds.refresh(Request())
            # Save refreshed token
            with open(token_path, 'w') as token:
                token.write(creds.to_json())

        # Build Keep service
        keep_service = build('keep', 'v1', credentials=creds)
        logger.info("Google Keep client initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Keep client: {e}")
        raise

# Create MCP server instance
server = Server("google-keep-mcp")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Google Keep tools"""
    return [
        types.Tool(
            name="create_note",
            description="Create a new Google Keep note",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Note title"
                    },
                    "body": {
                        "type": "string",
                        "description": "Note body content"
                    }
                },
                "required": ["body"]
            }
        ),
        types.Tool(
            name="list_notes",
            description="List all Google Keep notes",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_size": {
                        "type": "integer",
                        "description": "Number of notes to retrieve (default: 10, max: 100)"
                    }
                }
            }
        ),
        types.Tool(
            name="get_note",
            description="Get a specific Google Keep note",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "Note ID"
                    }
                },
                "required": ["note_id"]
            }
        ),
        types.Tool(
            name="update_note",
            description="Update an existing Google Keep note",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "Note ID"
                    },
                    "title": {
                        "type": "string",
                        "description": "New note title (optional)"
                    },
                    "body": {
                        "type": "string",
                        "description": "New note body (optional)"
                    }
                },
                "required": ["note_id"]
            }
        ),
        types.Tool(
            name="delete_note",
            description="Delete a Google Keep note",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "Note ID"
                    }
                },
                "required": ["note_id"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests"""

    if not keep_service:
        await init_keep_client()

    try:
        if name == "create_note":
            return await create_note_tool(arguments or {})
        elif name == "list_notes":
            return await list_notes_tool(arguments or {})
        elif name == "get_note":
            return await get_note_tool(arguments or {})
        elif name == "update_note":
            return await update_note_tool(arguments or {})
        elif name == "delete_note":
            return await delete_note_tool(arguments or {})
        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

async def create_note_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Create a new Google Keep note"""
    title = arguments.get("title", "")
    body = arguments.get("body", "")

    try:
        # Create note body
        note = {
            "body": {
                "text": {
                    "text": body
                }
            }
        }

        if title:
            note["title"] = title

        # Create the note
        result = keep_service.notes().create(body=note).execute()

        note_id = result.get("name", "").split("/")[-1]
        note_title = result.get("title", "Untitled")
        note_body = result.get("body", {}).get("text", {}).get("text", "")

        response_text = f"Note created successfully!\n"
        response_text += f"Note ID: {note_id}\n"
        response_text += f"Title: {note_title}\n"
        response_text += f"Body: {note_body[:100]}{'...' if len(note_body) > 100 else ''}"

        return [types.TextContent(type="text", text=response_text)]

    except HttpError as error:
        logger.error(f"Error creating note: {error}")
        return [types.TextContent(type="text", text=f"Error creating note: {error}")]

async def list_notes_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """List all Google Keep notes"""
    page_size = arguments.get("page_size", 10)
    if page_size > 100:
        page_size = 100

    try:
        result = keep_service.notes().list(pageSize=page_size).execute()

        notes = result.get("notes", [])

        if not notes:
            return [types.TextContent(type="text", text="No notes found.")]

        response_text = f"Found {len(notes)} note(s):\n\n"

        for idx, note in enumerate(notes, 1):
            note_id = note.get("name", "").split("/")[-1]
            title = note.get("title", "Untitled")
            body = note.get("body", {}).get("text", {}).get("text", "")
            create_time = note.get("createTime", "")
            update_time = note.get("updateTime", "")

            response_text += f"{idx}. {title}\n"
            response_text += f"   ID: {note_id}\n"
            response_text += f"   Body: {body[:80]}{'...' if len(body) > 80 else ''}\n"
            response_text += f"   Created: {create_time}\n"
            response_text += f"   Updated: {update_time}\n\n"

        return [types.TextContent(type="text", text=response_text)]

    except HttpError as error:
        logger.error(f"Error listing notes: {error}")
        return [types.TextContent(type="text", text=f"Error listing notes: {error}")]

async def get_note_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Get a specific Google Keep note"""
    note_id = arguments.get("note_id")

    if not note_id:
        return [types.TextContent(type="text", text="Error: note_id is required")]

    try:
        # Ensure note_id is in the correct format
        if not note_id.startswith("notes/"):
            note_id = f"notes/{note_id}"

        result = keep_service.notes().get(name=note_id).execute()

        title = result.get("title", "Untitled")
        body = result.get("body", {}).get("text", {}).get("text", "")
        create_time = result.get("createTime", "")
        update_time = result.get("updateTime", "")

        response_text = f"Title: {title}\n\n"
        response_text += f"Body:\n{body}\n\n"
        response_text += f"Created: {create_time}\n"
        response_text += f"Updated: {update_time}"

        return [types.TextContent(type="text", text=response_text)]

    except HttpError as error:
        logger.error(f"Error getting note: {error}")
        return [types.TextContent(type="text", text=f"Error getting note: {error}")]

async def update_note_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Update an existing Google Keep note"""
    note_id = arguments.get("note_id")
    title = arguments.get("title")
    body = arguments.get("body")

    if not note_id:
        return [types.TextContent(type="text", text="Error: note_id is required")]

    if not title and not body:
        return [types.TextContent(type="text", text="Error: At least one of title or body must be provided")]

    try:
        # Ensure note_id is in the correct format
        if not note_id.startswith("notes/"):
            note_id = f"notes/{note_id}"

        # Get current note
        current_note = keep_service.notes().get(name=note_id).execute()

        # Build update mask
        update_mask = []
        note_update = {}

        if title is not None:
            note_update["title"] = title
            update_mask.append("title")

        if body is not None:
            note_update["body"] = {
                "text": {
                    "text": body
                }
            }
            update_mask.append("body")

        note_update["name"] = note_id

        # Execute update
        result = keep_service.notes().patch(
            name=note_id,
            body=note_update,
            updateMask=",".join(update_mask)
        ).execute()

        return [types.TextContent(type="text", text="Note updated successfully")]

    except HttpError as error:
        logger.error(f"Error updating note: {error}")
        return [types.TextContent(type="text", text=f"Error updating note: {error}")]

async def delete_note_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Delete a Google Keep note"""
    note_id = arguments.get("note_id")

    if not note_id:
        return [types.TextContent(type="text", text="Error: note_id is required")]

    try:
        # Ensure note_id is in the correct format
        if not note_id.startswith("notes/"):
            note_id = f"notes/{note_id}"

        keep_service.notes().delete(name=note_id).execute()

        return [types.TextContent(type="text", text=f"Note {note_id} deleted successfully")]

    except HttpError as error:
        logger.error(f"Error deleting note: {error}")
        return [types.TextContent(type="text", text=f"Error deleting note: {error}")]

async def main():
    """Main entry point for the MCP server"""
    logger.info("Starting Google Keep MCP server...")

    # Initialize Keep client
    try:
        await init_keep_client()
    except Exception as e:
        logger.error(f"Failed to initialize Keep client: {e}")
        sys.exit(1)

    # Run the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Server running on stdio")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="google-keep-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
