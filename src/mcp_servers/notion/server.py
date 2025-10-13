"""Notion MCP Server - Provides tools to interact with Notion API

This server exposes tools for:
- Creating pages
- Reading pages
- Updating pages
- Querying databases
- Creating database entries
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

# Import Notion SDK
try:
    from notion_client import Client
    NOTION_AVAILABLE = True
    logger.info("Notion client imported successfully - version 2.5.0")
except ImportError as e:
    logger.error(f"Failed to import Notion client: {e}")
    NOTION_AVAILABLE = False
    sys.exit(1)

# Global Notion client
notion_client = None

async def init_notion_client():
    """Initialize Notion client"""
    global notion_client

    try:
        # Get Notion API token from environment
        notion_token = os.getenv("NOTION_TOKEN")

        if not notion_token:
            raise ValueError("NOTION_TOKEN environment variable not found")

        logger.info("Initializing Notion client...")
        notion_client = Client(auth=notion_token)
        logger.info("Notion client initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Notion client: {e}")
        raise

# Create MCP server instance
server = Server("notion-mcp")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Notion tools"""
    return [
        types.Tool(
            name="create_page",
            description="Create a new Notion page",
            inputSchema={
                "type": "object",
                "properties": {
                    "parent_id": {
                        "type": "string",
                        "description": "Parent page or database ID"
                    },
                    "title": {
                        "type": "string",
                        "description": "Page title"
                    },
                    "content": {
                        "type": "string",
                        "description": "Page content (markdown or plain text)"
                    }
                },
                "required": ["parent_id", "title"]
            }
        ),
        types.Tool(
            name="get_page",
            description="Get Notion page content",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "Page ID"
                    }
                },
                "required": ["page_id"]
            }
        ),
        types.Tool(
            name="update_page",
            description="Update Notion page properties",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "Page ID"
                    },
                    "title": {
                        "type": "string",
                        "description": "New page title"
                    }
                },
                "required": ["page_id"]
            }
        ),
        types.Tool(
            name="query_database",
            description="Query a Notion database",
            inputSchema={
                "type": "object",
                "properties": {
                    "database_id": {
                        "type": "string",
                        "description": "Database ID"
                    },
                    "filter": {
                        "type": "object",
                        "description": "Filter conditions (optional)"
                    },
                    "sorts": {
                        "type": "array",
                        "description": "Sort options (optional)"
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Number of results (default: 10, max: 100)"
                    }
                },
                "required": ["database_id"]
            }
        ),
        types.Tool(
            name="create_database_entry",
            description="Create a new entry in a Notion database",
            inputSchema={
                "type": "object",
                "properties": {
                    "database_id": {
                        "type": "string",
                        "description": "Database ID"
                    },
                    "properties": {
                        "type": "object",
                        "description": "Entry properties as key-value pairs"
                    }
                },
                "required": ["database_id", "properties"]
            }
        ),
        types.Tool(
            name="search",
            description="Search Notion workspace",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "filter": {
                        "type": "object",
                        "description": "Filter by type: page or database"
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

    if not notion_client:
        await init_notion_client()

    try:
        if name == "create_page":
            return await create_page_tool(arguments or {})
        elif name == "get_page":
            return await get_page_tool(arguments or {})
        elif name == "update_page":
            return await update_page_tool(arguments or {})
        elif name == "query_database":
            return await query_database_tool(arguments or {})
        elif name == "create_database_entry":
            return await create_database_entry_tool(arguments or {})
        elif name == "search":
            return await search_tool(arguments or {})
        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

async def create_page_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Create a new Notion page"""
    parent_id = arguments.get("parent_id")
    title = arguments.get("title", "Untitled")
    content = arguments.get("content", "")

    if not parent_id:
        return [types.TextContent(type="text", text="Error: parent_id is required")]

    try:
        # Create page properties
        properties = {
            "title": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            }
        }

        # Create page body
        children = []
        if content:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": content
                            }
                        }
                    ]
                }
            })

        # Create the page
        result = notion_client.pages.create(
            parent={"page_id": parent_id},
            properties=properties,
            children=children
        )

        page_id = result.get("id")
        page_url = result.get("url")

        response_text = f"Page created successfully!\n"
        response_text += f"Page ID: {page_id}\n"
        response_text += f"Title: {title}\n"
        response_text += f"URL: {page_url}"

        return [types.TextContent(type="text", text=response_text)]

    except Exception as error:
        logger.error(f"Error creating page: {error}")
        return [types.TextContent(type="text", text=f"Error creating page: {error}")]

async def get_page_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Get Notion page content"""
    page_id = arguments.get("page_id")

    if not page_id:
        return [types.TextContent(type="text", text="Error: page_id is required")]

    try:
        # Get page properties
        page = notion_client.pages.retrieve(page_id=page_id)

        # Get page blocks (content)
        blocks = notion_client.blocks.children.list(block_id=page_id)

        # Extract title
        title = "Untitled"
        properties = page.get("properties", {})
        for prop_name, prop_data in properties.items():
            if prop_data.get("type") == "title":
                title_array = prop_data.get("title", [])
                if title_array:
                    title = title_array[0].get("text", {}).get("content", "Untitled")
                break

        response_text = f"Page: {title}\n"
        response_text += f"ID: {page_id}\n"
        response_text += f"URL: {page.get('url')}\n\n"
        response_text += "Content:\n"

        # Extract block content
        for block in blocks.get("results", []):
            block_type = block.get("type")
            if block_type == "paragraph":
                rich_text = block.get("paragraph", {}).get("rich_text", [])
                for text_obj in rich_text:
                    response_text += text_obj.get("text", {}).get("content", "")
                response_text += "\n"

        return [types.TextContent(type="text", text=response_text)]

    except Exception as error:
        logger.error(f"Error getting page: {error}")
        return [types.TextContent(type="text", text=f"Error getting page: {error}")]

async def update_page_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Update Notion page properties"""
    page_id = arguments.get("page_id")
    title = arguments.get("title")

    if not page_id:
        return [types.TextContent(type="text", text="Error: page_id is required")]

    try:
        properties = {}

        if title:
            properties["title"] = {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            }

        result = notion_client.pages.update(
            page_id=page_id,
            properties=properties
        )

        return [types.TextContent(type="text", text="Page updated successfully")]

    except Exception as error:
        logger.error(f"Error updating page: {error}")
        return [types.TextContent(type="text", text=f"Error updating page: {error}")]

async def query_database_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Query a Notion database"""
    database_id = arguments.get("database_id")
    filter_obj = arguments.get("filter")
    sorts = arguments.get("sorts")
    page_size = arguments.get("page_size", 10)

    if not database_id:
        return [types.TextContent(type="text", text="Error: database_id is required")]

    try:
        query_params = {
            "database_id": database_id,
            "page_size": min(page_size, 100)
        }

        if filter_obj:
            query_params["filter"] = filter_obj
        if sorts:
            query_params["sorts"] = sorts

        result = notion_client.databases.query(**query_params)

        results = result.get("results", [])
        response_text = f"Found {len(results)} result(s):\n\n"

        for idx, page in enumerate(results, 1):
            page_id = page.get("id")
            properties = page.get("properties", {})

            # Extract title
            title = "Untitled"
            for prop_name, prop_data in properties.items():
                if prop_data.get("type") == "title":
                    title_array = prop_data.get("title", [])
                    if title_array:
                        title = title_array[0].get("text", {}).get("content", "Untitled")
                    break

            response_text += f"{idx}. {title}\n"
            response_text += f"   ID: {page_id}\n"
            response_text += f"   URL: {page.get('url')}\n\n"

        return [types.TextContent(type="text", text=response_text)]

    except Exception as error:
        logger.error(f"Error querying database: {error}")
        return [types.TextContent(type="text", text=f"Error querying database: {error}")]

async def create_database_entry_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Create a new entry in a Notion database"""
    database_id = arguments.get("database_id")
    properties = arguments.get("properties", {})

    if not database_id or not properties:
        return [types.TextContent(type="text", text="Error: database_id and properties are required")]

    try:
        result = notion_client.pages.create(
            parent={"database_id": database_id},
            properties=properties
        )

        page_id = result.get("id")
        page_url = result.get("url")

        response_text = f"Database entry created successfully!\n"
        response_text += f"Entry ID: {page_id}\n"
        response_text += f"URL: {page_url}"

        return [types.TextContent(type="text", text=response_text)]

    except Exception as error:
        logger.error(f"Error creating database entry: {error}")
        return [types.TextContent(type="text", text=f"Error creating database entry: {error}")]

async def search_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Search Notion workspace"""
    query = arguments.get("query")
    filter_obj = arguments.get("filter")

    if not query:
        return [types.TextContent(type="text", text="Error: query is required")]

    try:
        search_params = {"query": query}
        if filter_obj:
            search_params["filter"] = filter_obj

        result = notion_client.search(**search_params)

        results = result.get("results", [])
        response_text = f"Found {len(results)} result(s):\n\n"

        for idx, item in enumerate(results, 1):
            item_id = item.get("id")
            item_type = item.get("object")

            # Get title
            title = "Untitled"
            if item_type == "page":
                properties = item.get("properties", {})
                for prop_name, prop_data in properties.items():
                    if prop_data.get("type") == "title":
                        title_array = prop_data.get("title", [])
                        if title_array:
                            title = title_array[0].get("text", {}).get("content", "Untitled")
                        break

            response_text += f"{idx}. [{item_type.upper()}] {title}\n"
            response_text += f"   ID: {item_id}\n"
            response_text += f"   URL: {item.get('url')}\n\n"

        return [types.TextContent(type="text", text=response_text)]

    except Exception as error:
        logger.error(f"Error searching: {error}")
        return [types.TextContent(type="text", text=f"Error searching: {error}")]

async def main():
    """Main entry point for the MCP server"""
    logger.info("Starting Notion MCP server...")

    # Initialize Notion client
    try:
        await init_notion_client()
    except Exception as e:
        logger.error(f"Failed to initialize Notion client: {e}")
        sys.exit(1)

    # Run the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Server running on stdio")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="notion-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
