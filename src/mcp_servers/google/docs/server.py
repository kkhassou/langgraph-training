#!/usr/bin/env python3
"""
Google Docs MCP Server

A Model Context Protocol server that provides Google Docs integration capabilities.
This server allows AI assistants to interact with Google Docs through standardized MCP tools.
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

# Scopes for Docs API
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive.file'
]

# Global Docs service
docs_service = None
drive_service = None


async def init_docs_client():
    """Initialize Google Docs client with OAuth2 credentials"""
    global docs_service, drive_service

    if not GOOGLE_SDK_AVAILABLE:
        logger.warning("Google API client libraries not available")
        return False

    try:
        creds = None
        token_path = os.getenv("GOOGLE_TOKEN_PATH", os.getenv("DOCS_TOKEN_PATH", "token_docs.json"))
        credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", os.getenv("DOCS_CREDENTIALS_PATH", "credentials.json"))

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

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

            with open(token_path, 'w') as token:
                token.write(creds.to_json())

        docs_service = build('docs', 'v1', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)
        logger.info("Successfully connected to Google Docs")
        return True

    except Exception as e:
        logger.error(f"Failed to connect to Google Docs: {e}")
        docs_service = None
        drive_service = None
        return False


async def create_document_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new Google Document"""
    if not docs_service:
        raise Exception("Docs client is not initialized. Please check your Google Docs configuration.")

    try:
        title = arguments.get("title", "Untitled Document")

        document = {
            'title': title
        }

        result = docs_service.documents().create(body=document).execute()

        return {
            "document_id": result.get('documentId'),
            "title": result.get('title'),
            "document_url": f"https://docs.google.com/document/d/{result.get('documentId')}/edit",
            "status": "created"
        }

    except HttpError as error:
        logger.error(f"Docs API error in create_document: {error}")
        raise Exception(f"Docs API error: {str(error)}")


async def read_document_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Read content from a Google Document"""
    if not docs_service:
        raise Exception("Docs client is not initialized. Please check your Google Docs configuration.")

    try:
        document_id = arguments.get("document_id")

        if not document_id:
            raise ValueError("document_id is required")

        document = docs_service.documents().get(documentId=document_id).execute()

        # Extract text content
        content = document.get('body', {}).get('content', [])
        text_content = []

        for element in content:
            if 'paragraph' in element:
                paragraph = element['paragraph']
                for elem in paragraph.get('elements', []):
                    if 'textRun' in elem:
                        text_content.append(elem['textRun'].get('content', ''))

        full_text = ''.join(text_content)

        return {
            "document_id": document.get('documentId'),
            "title": document.get('title'),
            "content": full_text,
            "revision_id": document.get('revisionId'),
            "char_count": len(full_text)
        }

    except HttpError as error:
        logger.error(f"Docs API error in read_document: {error}")
        raise Exception(f"Docs API error: {str(error)}")


async def append_text_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Append text to a Google Document"""
    if not docs_service:
        raise Exception("Docs client is not initialized. Please check your Google Docs configuration.")

    try:
        document_id = arguments.get("document_id")
        text = arguments.get("text")

        if not document_id:
            raise ValueError("document_id is required")
        if not text:
            raise ValueError("text is required")

        requests = [
            {
                'insertText': {
                    'location': {
                        'index': 1
                    },
                    'text': text
                }
            }
        ]

        result = docs_service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute()

        return {
            "document_id": document_id,
            "status": "appended",
            "replies": result.get('replies', [])
        }

    except HttpError as error:
        logger.error(f"Docs API error in append_text: {error}")
        raise Exception(f"Docs API error: {str(error)}")


async def replace_text_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Replace text in a Google Document"""
    if not docs_service:
        raise Exception("Docs client is not initialized. Please check your Google Docs configuration.")

    try:
        document_id = arguments.get("document_id")
        find_text = arguments.get("find_text")
        replace_text = arguments.get("replace_text")

        if not document_id:
            raise ValueError("document_id is required")
        if not find_text:
            raise ValueError("find_text is required")
        if replace_text is None:
            raise ValueError("replace_text is required")

        requests = [
            {
                'replaceAllText': {
                    'containsText': {
                        'text': find_text,
                        'matchCase': arguments.get("match_case", False)
                    },
                    'replaceText': replace_text
                }
            }
        ]

        result = docs_service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute()

        return {
            "document_id": document_id,
            "status": "replaced",
            "occurrences_changed": result.get('replies', [{}])[0].get('replaceAllText', {}).get('occurrencesChanged', 0)
        }

    except HttpError as error:
        logger.error(f"Docs API error in replace_text: {error}")
        raise Exception(f"Docs API error: {str(error)}")


async def insert_text_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Insert text at a specific location in a Google Document"""
    if not docs_service:
        raise Exception("Docs client is not initialized. Please check your Google Docs configuration.")

    try:
        document_id = arguments.get("document_id")
        text = arguments.get("text")
        index = arguments.get("index", 1)

        if not document_id:
            raise ValueError("document_id is required")
        if not text:
            raise ValueError("text is required")

        requests = [
            {
                'insertText': {
                    'location': {
                        'index': index
                    },
                    'text': text
                }
            }
        ]

        result = docs_service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute()

        return {
            "document_id": document_id,
            "status": "inserted",
            "index": index,
            "text_length": len(text)
        }

    except HttpError as error:
        logger.error(f"Docs API error in insert_text: {error}")
        raise Exception(f"Docs API error: {str(error)}")


# Create the MCP server
app = Server("docs-mcp-server")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available Google Docs tools"""
    return [
        Tool(
            name="create_document",
            description="Create a new Google Document",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the document",
                        "default": "Untitled Document"
                    }
                }
            }
        ),
        Tool(
            name="read_document",
            description="Read content from a Google Document",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Document ID (from URL)"
                    }
                },
                "required": ["document_id"]
            }
        ),
        Tool(
            name="append_text",
            description="Append text to the end of a Google Document",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Document ID (from URL)"
                    },
                    "text": {
                        "type": "string",
                        "description": "Text to append"
                    }
                },
                "required": ["document_id", "text"]
            }
        ),
        Tool(
            name="insert_text",
            description="Insert text at a specific location in a Google Document",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Document ID (from URL)"
                    },
                    "text": {
                        "type": "string",
                        "description": "Text to insert"
                    },
                    "index": {
                        "type": "integer",
                        "description": "Character index where to insert (default: 1)",
                        "default": 1
                    }
                },
                "required": ["document_id", "text"]
            }
        ),
        Tool(
            name="replace_text",
            description="Replace all occurrences of text in a Google Document",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Document ID (from URL)"
                    },
                    "find_text": {
                        "type": "string",
                        "description": "Text to find"
                    },
                    "replace_text": {
                        "type": "string",
                        "description": "Text to replace with"
                    },
                    "match_case": {
                        "type": "boolean",
                        "description": "Whether to match case (default: false)",
                        "default": False
                    }
                },
                "required": ["document_id", "find_text", "replace_text"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls"""
    try:
        if name == "create_document":
            result = await create_document_tool(arguments)
            return [
                TextContent(
                    type="text",
                    text=f"✅ Document created successfully\nTitle: {result['title']}\nID: {result['document_id']}\nURL: {result['document_url']}"
                )
            ]

        elif name == "read_document":
            result = await read_document_tool(arguments)
            content_preview = result['content'][:500] if len(result['content']) > 500 else result['content']
            return [
                TextContent(
                    type="text",
                    text=f"📄 Document: {result['title']}\nCharacters: {result['char_count']}\n\nContent:\n{content_preview}{'...' if len(result['content']) > 500 else ''}"
                )
            ]

        elif name == "append_text":
            result = await append_text_tool(arguments)
            return [
                TextContent(
                    type="text",
                    text=f"✅ Text appended successfully\nDocument ID: {result['document_id']}"
                )
            ]

        elif name == "insert_text":
            result = await insert_text_tool(arguments)
            return [
                TextContent(
                    type="text",
                    text=f"✅ Text inserted successfully\nDocument ID: {result['document_id']}\nInserted {result['text_length']} characters at index {result['index']}"
                )
            ]

        elif name == "replace_text":
            result = await replace_text_tool(arguments)
            return [
                TextContent(
                    type="text",
                    text=f"✅ Text replaced successfully\nDocument ID: {result['document_id']}\nOccurrences changed: {result['occurrences_changed']}"
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
    await init_docs_client()

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
