#!/usr/bin/env python3
"""
Google Sheets MCP Server

A Model Context Protocol server that provides Google Sheets integration capabilities.
This server allows AI assistants to interact with Google Sheets through standardized MCP tools.
"""

import asyncio
import os
import logging
from typing import Any, Dict, List, Optional, Sequence
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_SDK_AVAILABLE = True
except ImportError:
    GOOGLE_SDK_AVAILABLE = False
    HttpError = Exception

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

# If modifying these scopes, delete the token file.
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

# Global Sheets service
sheets_service = None
drive_service = None


async def init_sheets_client():
    """Initialize Google Sheets client with OAuth2 credentials"""
    global sheets_service, drive_service

    if not GOOGLE_SDK_AVAILABLE:
        logger.warning("Google API client libraries not available")
        return False

    try:
        creds = None
        # The file token stores the user's access and refresh tokens
        token_path = os.getenv("GOOGLE_TOKEN_PATH", os.getenv("SHEETS_TOKEN_PATH", "token_sheets.json"))
        credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", os.getenv("SHEETS_CREDENTIALS_PATH", "credentials.json"))

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(credentials_path):
                    logger.error(f"Credentials file not found: {credentials_path}")
                    return False

                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(token_path, 'w') as token:
                token.write(creds.to_json())

        sheets_service = build('sheets', 'v4', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)
        logger.info("Successfully connected to Google Sheets")
        return True

    except Exception as e:
        logger.error(f"Failed to connect to Google Sheets: {e}")
        sheets_service = None
        drive_service = None
        return False


async def create_spreadsheet_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new Google Spreadsheet"""
    if not sheets_service:
        raise Exception("Sheets client is not initialized. Please check your Google Sheets configuration.")

    try:
        title = arguments.get("title", "Untitled Spreadsheet")

        spreadsheet = {
            'properties': {
                'title': title
            }
        }

        result = sheets_service.spreadsheets().create(body=spreadsheet).execute()

        return {
            "spreadsheet_id": result.get('spreadsheetId'),
            "spreadsheet_url": result.get('spreadsheetUrl'),
            "title": result.get('properties', {}).get('title'),
            "status": "created"
        }

    except HttpError as error:
        logger.error(f"Sheets API error in create_spreadsheet: {error}")
        raise Exception(f"Sheets API error: {str(error)}")


async def read_range_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Read data from a range in a Google Spreadsheet"""
    if not sheets_service:
        raise Exception("Sheets client is not initialized. Please check your Google Sheets configuration.")

    try:
        spreadsheet_id = arguments.get("spreadsheet_id")
        range_name = arguments.get("range", "Sheet1!A1:Z1000")

        if not spreadsheet_id:
            raise ValueError("spreadsheet_id is required")

        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()

        values = result.get('values', [])

        return {
            "range": result.get('range'),
            "values": values,
            "row_count": len(values),
            "column_count": len(values[0]) if values else 0
        }

    except HttpError as error:
        logger.error(f"Sheets API error in read_range: {error}")
        raise Exception(f"Sheets API error: {str(error)}")


async def write_range_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Write data to a range in a Google Spreadsheet"""
    if not sheets_service:
        raise Exception("Sheets client is not initialized. Please check your Google Sheets configuration.")

    try:
        spreadsheet_id = arguments.get("spreadsheet_id")
        range_name = arguments.get("range", "Sheet1!A1")
        values = arguments.get("values", [])

        if not spreadsheet_id:
            raise ValueError("spreadsheet_id is required")
        if not values:
            raise ValueError("values are required")

        body = {
            'values': values
        }

        result = sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()

        return {
            "updated_range": result.get('updatedRange'),
            "updated_rows": result.get('updatedRows'),
            "updated_columns": result.get('updatedColumns'),
            "updated_cells": result.get('updatedCells'),
            "status": "updated"
        }

    except HttpError as error:
        logger.error(f"Sheets API error in write_range: {error}")
        raise Exception(f"Sheets API error: {str(error)}")


async def append_rows_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Append rows to a Google Spreadsheet"""
    if not sheets_service:
        raise Exception("Sheets client is not initialized. Please check your Google Sheets configuration.")

    try:
        spreadsheet_id = arguments.get("spreadsheet_id")
        range_name = arguments.get("range", "Sheet1!A1")
        values = arguments.get("values", [])

        if not spreadsheet_id:
            raise ValueError("spreadsheet_id is required")
        if not values:
            raise ValueError("values are required")

        body = {
            'values': values
        }

        result = sheets_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()

        return {
            "updated_range": result.get('updates', {}).get('updatedRange'),
            "updated_rows": result.get('updates', {}).get('updatedRows'),
            "updated_cells": result.get('updates', {}).get('updatedCells'),
            "status": "appended"
        }

    except HttpError as error:
        logger.error(f"Sheets API error in append_rows: {error}")
        raise Exception(f"Sheets API error: {str(error)}")


async def clear_range_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Clear data from a range in a Google Spreadsheet"""
    if not sheets_service:
        raise Exception("Sheets client is not initialized. Please check your Google Sheets configuration.")

    try:
        spreadsheet_id = arguments.get("spreadsheet_id")
        range_name = arguments.get("range", "Sheet1!A1:Z1000")

        if not spreadsheet_id:
            raise ValueError("spreadsheet_id is required")

        result = sheets_service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()

        return {
            "cleared_range": result.get('clearedRange'),
            "status": "cleared"
        }

    except HttpError as error:
        logger.error(f"Sheets API error in clear_range: {error}")
        raise Exception(f"Sheets API error: {str(error)}")


async def get_spreadsheet_info_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Get information about a Google Spreadsheet"""
    if not sheets_service:
        raise Exception("Sheets client is not initialized. Please check your Google Sheets configuration.")

    try:
        spreadsheet_id = arguments.get("spreadsheet_id")

        if not spreadsheet_id:
            raise ValueError("spreadsheet_id is required")

        result = sheets_service.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()

        sheets = []
        for sheet in result.get('sheets', []):
            props = sheet.get('properties', {})
            sheets.append({
                "sheet_id": props.get('sheetId'),
                "title": props.get('title'),
                "index": props.get('index'),
                "row_count": props.get('gridProperties', {}).get('rowCount'),
                "column_count": props.get('gridProperties', {}).get('columnCount')
            })

        return {
            "spreadsheet_id": result.get('spreadsheetId'),
            "title": result.get('properties', {}).get('title'),
            "locale": result.get('properties', {}).get('locale'),
            "time_zone": result.get('properties', {}).get('timeZone'),
            "sheets": sheets
        }

    except HttpError as error:
        logger.error(f"Sheets API error in get_spreadsheet_info: {error}")
        raise Exception(f"Sheets API error: {str(error)}")


# Create the MCP server
app = Server("sheets-mcp-server")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available Google Sheets tools"""
    return [
        Tool(
            name="create_spreadsheet",
            description="Create a new Google Spreadsheet",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the spreadsheet",
                        "default": "Untitled Spreadsheet"
                    }
                }
            }
        ),
        Tool(
            name="read_range",
            description="Read data from a range in a Google Spreadsheet",
            inputSchema={
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "Spreadsheet ID (from URL)"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range in A1 notation (e.g., 'Sheet1!A1:D10')",
                        "default": "Sheet1!A1:Z1000"
                    }
                },
                "required": ["spreadsheet_id"]
            }
        ),
        Tool(
            name="write_range",
            description="Write data to a range in a Google Spreadsheet",
            inputSchema={
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "Spreadsheet ID (from URL)"
                    },
                    "range": {
                        "type": "string",
                        "description": "Starting range in A1 notation (e.g., 'Sheet1!A1')",
                        "default": "Sheet1!A1"
                    },
                    "values": {
                        "type": "array",
                        "items": {"type": "array"},
                        "description": "2D array of values to write (e.g., [['A1', 'B1'], ['A2', 'B2']])"
                    }
                },
                "required": ["spreadsheet_id", "values"]
            }
        ),
        Tool(
            name="append_rows",
            description="Append rows to the end of a Google Spreadsheet",
            inputSchema={
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "Spreadsheet ID (from URL)"
                    },
                    "range": {
                        "type": "string",
                        "description": "Sheet name (e.g., 'Sheet1!A1')",
                        "default": "Sheet1!A1"
                    },
                    "values": {
                        "type": "array",
                        "items": {"type": "array"},
                        "description": "2D array of values to append"
                    }
                },
                "required": ["spreadsheet_id", "values"]
            }
        ),
        Tool(
            name="clear_range",
            description="Clear data from a range in a Google Spreadsheet",
            inputSchema={
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "Spreadsheet ID (from URL)"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range in A1 notation (e.g., 'Sheet1!A1:D10')",
                        "default": "Sheet1!A1:Z1000"
                    }
                },
                "required": ["spreadsheet_id"]
            }
        ),
        Tool(
            name="get_spreadsheet_info",
            description="Get information about a Google Spreadsheet (sheets, dimensions, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "Spreadsheet ID (from URL)"
                    }
                },
                "required": ["spreadsheet_id"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls"""
    try:
        if name == "create_spreadsheet":
            result = await create_spreadsheet_tool(arguments)
            return [
                TextContent(
                    type="text",
                    text=f"✅ Spreadsheet created successfully\nTitle: {result['title']}\nID: {result['spreadsheet_id']}\nURL: {result['spreadsheet_url']}"
                )
            ]

        elif name == "read_range":
            result = await read_range_tool(arguments)
            spreadsheet_id = arguments.get("spreadsheet_id", "unknown")

            if not result['values']:
                return [TextContent(type="text", text=f"No data found in range {result['range']}")]

            # Format the data as a table
            data_text = f"📊 Data from {result['range']}:\n"
            data_text += f"Rows: {result['row_count']}, Columns: {result['column_count']}\n\n"

            for row in result['values'][:20]:  # Show first 20 rows
                data_text += " | ".join(str(cell) for cell in row) + "\n"

            if result['row_count'] > 20:
                data_text += f"\n... and {result['row_count'] - 20} more rows"

            return [TextContent(type="text", text=data_text)]

        elif name == "write_range":
            result = await write_range_tool(arguments)
            return [
                TextContent(
                    type="text",
                    text=f"✅ Data written successfully\nRange: {result['updated_range']}\nUpdated: {result['updated_cells']} cells ({result['updated_rows']} rows × {result['updated_columns']} columns)"
                )
            ]

        elif name == "append_rows":
            result = await append_rows_tool(arguments)
            return [
                TextContent(
                    type="text",
                    text=f"✅ Rows appended successfully\nRange: {result['updated_range']}\nAdded: {result['updated_rows']} rows ({result['updated_cells']} cells)"
                )
            ]

        elif name == "clear_range":
            result = await clear_range_tool(arguments)
            return [
                TextContent(
                    type="text",
                    text=f"✅ Range cleared successfully\nCleared range: {result['cleared_range']}"
                )
            ]

        elif name == "get_spreadsheet_info":
            result = await get_spreadsheet_info_tool(arguments)

            info_text = f"📊 Spreadsheet: {result['title']}\n"
            info_text += f"ID: {result['spreadsheet_id']}\n"
            info_text += f"Locale: {result['locale']}, Time Zone: {result['time_zone']}\n\n"
            info_text += f"Sheets ({len(result['sheets'])}):\n"

            for sheet in result['sheets']:
                info_text += f"  • {sheet['title']}: {sheet['row_count']} rows × {sheet['column_count']} columns\n"

            return [TextContent(type="text", text=info_text)]

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
    # Initialize Sheets client
    await init_sheets_client()

    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
