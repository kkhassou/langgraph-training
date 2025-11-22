#!/usr/bin/env python3
"""
Google Slides MCP Server

A Model Context Protocol server that provides Google Slides integration capabilities.
This server allows AI assistants to interact with Google Slides through standardized MCP tools.
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

# Scopes for Slides API
SCOPES = [
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/drive.file'
]

# Global Slides service
slides_service = None
drive_service = None


async def init_slides_client():
    """Initialize Google Slides client with OAuth2 credentials"""
    global slides_service, drive_service

    if not GOOGLE_SDK_AVAILABLE:
        logger.warning("Google API client libraries not available")
        return False

    try:
        creds = None
        token_path = os.getenv("GOOGLE_TOKEN_PATH", os.getenv("SLIDES_TOKEN_PATH", "token_slides.json"))
        credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", os.getenv("SLIDES_CREDENTIALS_PATH", "credentials.json"))

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

        slides_service = build('slides', 'v1', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)
        logger.info("Successfully connected to Google Slides")
        return True

    except Exception as e:
        logger.error(f"Failed to connect to Google Slides: {e}")
        slides_service = None
        drive_service = None
        return False


async def create_presentation_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new Google Slides presentation"""
    if not slides_service:
        raise Exception("Slides client is not initialized. Please check your Google Slides configuration.")

    try:
        title = arguments.get("title", "Untitled Presentation")

        presentation = {
            'title': title
        }

        result = slides_service.presentations().create(body=presentation).execute()

        return {
            "presentation_id": result.get('presentationId'),
            "title": result.get('title'),
            "presentation_url": f"https://docs.google.com/presentation/d/{result.get('presentationId')}/edit",
            "status": "created"
        }

    except HttpError as error:
        logger.error(f"Slides API error in create_presentation: {error}")
        raise Exception(f"Slides API error: {str(error)}")


async def read_presentation_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Read content from a Google Slides presentation"""
    if not slides_service:
        raise Exception("Slides client is not initialized. Please check your Google Slides configuration.")

    try:
        presentation_id = arguments.get("presentation_id")

        if not presentation_id:
            raise ValueError("presentation_id is required")

        presentation = slides_service.presentations().get(
            presentationId=presentation_id
        ).execute()

        slides = []
        for slide in presentation.get('slides', []):
            slide_info = {
                "object_id": slide.get('objectId'),
                "page_elements": []
            }

            for element in slide.get('pageElements', []):
                if 'shape' in element and 'text' in element['shape']:
                    text_elements = element['shape']['text'].get('textElements', [])
                    text_content = ''.join([
                        te.get('textRun', {}).get('content', '')
                        for te in text_elements
                        if 'textRun' in te
                    ])
                    if text_content.strip():
                        slide_info['page_elements'].append({
                            "type": "text",
                            "content": text_content.strip()
                        })

            slides.append(slide_info)

        return {
            "presentation_id": presentation.get('presentationId'),
            "title": presentation.get('title'),
            "slide_count": len(slides),
            "slides": slides
        }

    except HttpError as error:
        logger.error(f"Slides API error in read_presentation: {error}")
        raise Exception(f"Slides API error: {str(error)}")


async def add_slide_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Add a new slide to a presentation"""
    if not slides_service:
        raise Exception("Slides client is not initialized. Please check your Google Slides configuration.")

    try:
        presentation_id = arguments.get("presentation_id")
        index = arguments.get("index")

        if not presentation_id:
            raise ValueError("presentation_id is required")

        requests = [
            {
                'createSlide': {
                    'insertionIndex': index
                } if index is not None else {}
            }
        ]

        result = slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()

        created_slide = result.get('replies', [{}])[0].get('createSlide', {})

        return {
            "presentation_id": presentation_id,
            "slide_id": created_slide.get('objectId'),
            "status": "added"
        }

    except HttpError as error:
        logger.error(f"Slides API error in add_slide: {error}")
        raise Exception(f"Slides API error: {str(error)}")


async def add_text_to_slide_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Add text to a slide"""
    if not slides_service:
        raise Exception("Slides client is not initialized. Please check your Google Slides configuration.")

    try:
        presentation_id = arguments.get("presentation_id")
        slide_id = arguments.get("slide_id")
        text = arguments.get("text")

        if not presentation_id:
            raise ValueError("presentation_id is required")
        if not slide_id:
            raise ValueError("slide_id is required")
        if not text:
            raise ValueError("text is required")

        # Generate a unique ID for the text box
        text_box_id = f"TextBox_{slide_id}"

        requests = [
            {
                'createShape': {
                    'objectId': text_box_id,
                    'shapeType': 'TEXT_BOX',
                    'elementProperties': {
                        'pageObjectId': slide_id,
                        'size': {
                            'height': {'magnitude': 100, 'unit': 'PT'},
                            'width': {'magnitude': 400, 'unit': 'PT'}
                        },
                        'transform': {
                            'scaleX': 1,
                            'scaleY': 1,
                            'translateX': 100,
                            'translateY': 100,
                            'unit': 'PT'
                        }
                    }
                }
            },
            {
                'insertText': {
                    'objectId': text_box_id,
                    'text': text
                }
            }
        ]

        result = slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()

        return {
            "presentation_id": presentation_id,
            "slide_id": slide_id,
            "text_box_id": text_box_id,
            "status": "text_added"
        }

    except HttpError as error:
        logger.error(f"Slides API error in add_text_to_slide: {error}")
        raise Exception(f"Slides API error: {str(error)}")


async def delete_slide_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Delete a slide from a presentation"""
    if not slides_service:
        raise Exception("Slides client is not initialized. Please check your Google Slides configuration.")

    try:
        presentation_id = arguments.get("presentation_id")
        slide_id = arguments.get("slide_id")

        if not presentation_id:
            raise ValueError("presentation_id is required")
        if not slide_id:
            raise ValueError("slide_id is required")

        requests = [
            {
                'deleteObject': {
                    'objectId': slide_id
                }
            }
        ]

        result = slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()

        return {
            "presentation_id": presentation_id,
            "slide_id": slide_id,
            "status": "deleted"
        }

    except HttpError as error:
        logger.error(f"Slides API error in delete_slide: {error}")
        raise Exception(f"Slides API error: {str(error)}")


# Create the MCP server
app = Server("slides-mcp-server")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available Google Slides tools"""
    return [
        Tool(
            name="create_presentation",
            description="Create a new Google Slides presentation",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the presentation",
                        "default": "Untitled Presentation"
                    }
                }
            }
        ),
        Tool(
            name="read_presentation",
            description="Read content from a Google Slides presentation",
            inputSchema={
                "type": "object",
                "properties": {
                    "presentation_id": {
                        "type": "string",
                        "description": "Presentation ID (from URL)"
                    }
                },
                "required": ["presentation_id"]
            }
        ),
        Tool(
            name="add_slide",
            description="Add a new slide to a presentation",
            inputSchema={
                "type": "object",
                "properties": {
                    "presentation_id": {
                        "type": "string",
                        "description": "Presentation ID (from URL)"
                    },
                    "index": {
                        "type": "integer",
                        "description": "Position to insert slide (optional, defaults to end)"
                    }
                },
                "required": ["presentation_id"]
            }
        ),
        Tool(
            name="add_text_to_slide",
            description="Add text to a specific slide",
            inputSchema={
                "type": "object",
                "properties": {
                    "presentation_id": {
                        "type": "string",
                        "description": "Presentation ID (from URL)"
                    },
                    "slide_id": {
                        "type": "string",
                        "description": "Slide object ID"
                    },
                    "text": {
                        "type": "string",
                        "description": "Text to add"
                    }
                },
                "required": ["presentation_id", "slide_id", "text"]
            }
        ),
        Tool(
            name="delete_slide",
            description="Delete a slide from a presentation",
            inputSchema={
                "type": "object",
                "properties": {
                    "presentation_id": {
                        "type": "string",
                        "description": "Presentation ID (from URL)"
                    },
                    "slide_id": {
                        "type": "string",
                        "description": "Slide object ID to delete"
                    }
                },
                "required": ["presentation_id", "slide_id"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls"""
    try:
        if name == "create_presentation":
            result = await create_presentation_tool(arguments)
            return [
                TextContent(
                    type="text",
                    text=f"✅ Presentation created successfully\nTitle: {result['title']}\nID: {result['presentation_id']}\nURL: {result['presentation_url']}"
                )
            ]

        elif name == "read_presentation":
            result = await read_presentation_tool(arguments)
            text = f"📊 Presentation: {result['title']}\nSlides: {result['slide_count']}\n\n"

            for i, slide in enumerate(result['slides'], 1):
                text += f"Slide {i} (ID: {slide['object_id']}):\n"
                for element in slide['page_elements']:
                    if element['type'] == 'text':
                        text += f"  • {element['content'][:100]}{'...' if len(element['content']) > 100 else ''}\n"
                text += "\n"

            return [TextContent(type="text", text=text)]

        elif name == "add_slide":
            result = await add_slide_tool(arguments)
            return [
                TextContent(
                    type="text",
                    text=f"✅ Slide added successfully\nPresentation ID: {result['presentation_id']}\nSlide ID: {result['slide_id']}"
                )
            ]

        elif name == "add_text_to_slide":
            result = await add_text_to_slide_tool(arguments)
            return [
                TextContent(
                    type="text",
                    text=f"✅ Text added successfully\nPresentation ID: {result['presentation_id']}\nSlide ID: {result['slide_id']}"
                )
            ]

        elif name == "delete_slide":
            result = await delete_slide_tool(arguments)
            return [
                TextContent(
                    type="text",
                    text=f"✅ Slide deleted successfully\nPresentation ID: {result['presentation_id']}\nSlide ID: {result['slide_id']}"
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
    await init_slides_client()

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
