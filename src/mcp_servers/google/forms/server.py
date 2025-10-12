"""Google Forms MCP Server - Provides tools to interact with Google Forms API

This server exposes tools for:
- Creating forms
- Reading form structure
- Getting form responses
- Listing form responses
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

# Google Forms API scopes
SCOPES = [
    'https://www.googleapis.com/auth/forms.body',
    'https://www.googleapis.com/auth/forms.responses.readonly'
]

# Global Forms service
forms_service = None

async def init_forms_client():
    """Initialize Google Forms API client"""
    global forms_service

    try:
        # Get token and credentials paths from environment
        token_path = os.getenv(
            "GOOGLE_TOKEN_PATH",
            os.getenv("FORMS_TOKEN_PATH", "secrets/google_token.json")
        )
        credentials_path = os.getenv(
            "GOOGLE_CREDENTIALS_PATH",
            os.getenv("FORMS_CREDENTIALS_PATH", "secrets/google_credentials.json")
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

        # Build Forms service
        forms_service = build('forms', 'v1', credentials=creds)
        logger.info("Google Forms client initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Forms client: {e}")
        raise

# Create MCP server instance
server = Server("google-forms-mcp")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Google Forms tools"""
    return [
        types.Tool(
            name="create_form",
            description="Create a new Google Form",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Form title"
                    },
                    "description": {
                        "type": "string",
                        "description": "Form description (optional)"
                    }
                },
                "required": ["title"]
            }
        ),
        types.Tool(
            name="get_form",
            description="Get form structure and metadata",
            inputSchema={
                "type": "object",
                "properties": {
                    "form_id": {
                        "type": "string",
                        "description": "Form ID from URL"
                    }
                },
                "required": ["form_id"]
            }
        ),
        types.Tool(
            name="list_responses",
            description="List all responses for a form",
            inputSchema={
                "type": "object",
                "properties": {
                    "form_id": {
                        "type": "string",
                        "description": "Form ID from URL"
                    }
                },
                "required": ["form_id"]
            }
        ),
        types.Tool(
            name="get_response",
            description="Get a specific form response",
            inputSchema={
                "type": "object",
                "properties": {
                    "form_id": {
                        "type": "string",
                        "description": "Form ID from URL"
                    },
                    "response_id": {
                        "type": "string",
                        "description": "Response ID"
                    }
                },
                "required": ["form_id", "response_id"]
            }
        ),
        types.Tool(
            name="update_form",
            description="Update form title or description",
            inputSchema={
                "type": "object",
                "properties": {
                    "form_id": {
                        "type": "string",
                        "description": "Form ID from URL"
                    },
                    "title": {
                        "type": "string",
                        "description": "New form title (optional)"
                    },
                    "description": {
                        "type": "string",
                        "description": "New form description (optional)"
                    }
                },
                "required": ["form_id"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests"""

    if not forms_service:
        await init_forms_client()

    try:
        if name == "create_form":
            return await create_form_tool(arguments or {})
        elif name == "get_form":
            return await get_form_tool(arguments or {})
        elif name == "list_responses":
            return await list_responses_tool(arguments or {})
        elif name == "get_response":
            return await get_response_tool(arguments or {})
        elif name == "update_form":
            return await update_form_tool(arguments or {})
        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

async def create_form_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Create a new Google Form"""
    title = arguments.get("title", "Untitled Form")
    description = arguments.get("description", "")

    try:
        # Create form body
        form_body = {
            "info": {
                "title": title
            }
        }

        if description:
            form_body["info"]["documentTitle"] = description

        # Create the form
        result = forms_service.forms().create(body=form_body).execute()

        form_id = result.get("formId")
        responder_uri = result.get("responderUri")

        response_text = f"Form created successfully!\n"
        response_text += f"Form ID: {form_id}\n"
        response_text += f"Form URL: {responder_uri}\n"
        response_text += f"Edit URL: https://docs.google.com/forms/d/{form_id}/edit"

        return [types.TextContent(type="text", text=response_text)]

    except HttpError as error:
        logger.error(f"Error creating form: {error}")
        return [types.TextContent(type="text", text=f"Error creating form: {error}")]

async def get_form_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Get form structure and metadata"""
    form_id = arguments.get("form_id")

    if not form_id:
        return [types.TextContent(type="text", text="Error: form_id is required")]

    try:
        result = forms_service.forms().get(formId=form_id).execute()

        title = result.get("info", {}).get("title", "Untitled")
        description = result.get("info", {}).get("description", "")
        responder_uri = result.get("responderUri", "")

        response_text = f"Form: {title}\n"
        if description:
            response_text += f"Description: {description}\n"
        response_text += f"Form URL: {responder_uri}\n\n"

        # List questions
        items = result.get("items", [])
        if items:
            response_text += f"Questions ({len(items)}):\n"
            for idx, item in enumerate(items, 1):
                question = item.get("title", "")
                question_type = list(item.keys())[1] if len(item.keys()) > 1 else "unknown"
                response_text += f"{idx}. {question} ({question_type})\n"
        else:
            response_text += "No questions in this form yet.\n"

        return [types.TextContent(type="text", text=response_text)]

    except HttpError as error:
        logger.error(f"Error getting form: {error}")
        return [types.TextContent(type="text", text=f"Error getting form: {error}")]

async def list_responses_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """List all responses for a form"""
    form_id = arguments.get("form_id")

    if not form_id:
        return [types.TextContent(type="text", text="Error: form_id is required")]

    try:
        result = forms_service.forms().responses().list(formId=form_id).execute()

        responses = result.get("responses", [])

        if not responses:
            return [types.TextContent(type="text", text="No responses found for this form.")]

        response_text = f"Found {len(responses)} response(s):\n\n"

        for idx, response in enumerate(responses, 1):
            response_id = response.get("responseId")
            create_time = response.get("createTime", "Unknown time")
            last_submitted = response.get("lastSubmittedTime", create_time)

            response_text += f"{idx}. Response ID: {response_id}\n"
            response_text += f"   Submitted: {last_submitted}\n"

            # Get answers
            answers = response.get("answers", {})
            if answers:
                response_text += "   Answers:\n"
                for question_id, answer_data in answers.items():
                    text_answers = answer_data.get("textAnswers", {}).get("answers", [])
                    if text_answers:
                        for answer in text_answers:
                            value = answer.get("value", "")
                            response_text += f"     - {value}\n"

            response_text += "\n"

        return [types.TextContent(type="text", text=response_text)]

    except HttpError as error:
        logger.error(f"Error listing responses: {error}")
        return [types.TextContent(type="text", text=f"Error listing responses: {error}")]

async def get_response_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Get a specific form response"""
    form_id = arguments.get("form_id")
    response_id = arguments.get("response_id")

    if not form_id or not response_id:
        return [types.TextContent(type="text", text="Error: form_id and response_id are required")]

    try:
        result = forms_service.forms().responses().get(
            formId=form_id,
            responseId=response_id
        ).execute()

        create_time = result.get("createTime", "Unknown")
        last_submitted = result.get("lastSubmittedTime", create_time)

        response_text = f"Response ID: {response_id}\n"
        response_text += f"Submitted: {last_submitted}\n\n"
        response_text += "Answers:\n"

        answers = result.get("answers", {})
        for question_id, answer_data in answers.items():
            text_answers = answer_data.get("textAnswers", {}).get("answers", [])
            if text_answers:
                for answer in text_answers:
                    value = answer.get("value", "")
                    response_text += f"  {value}\n"

        return [types.TextContent(type="text", text=response_text)]

    except HttpError as error:
        logger.error(f"Error getting response: {error}")
        return [types.TextContent(type="text", text=f"Error getting response: {error}")]

async def update_form_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Update form title or description"""
    form_id = arguments.get("form_id")
    title = arguments.get("title")
    description = arguments.get("description")

    if not form_id:
        return [types.TextContent(type="text", text="Error: form_id is required")]

    if not title and not description:
        return [types.TextContent(type="text", text="Error: At least one of title or description must be provided")]

    try:
        # Build update requests
        requests = []

        if title:
            requests.append({
                "updateFormInfo": {
                    "info": {
                        "title": title
                    },
                    "updateMask": "title"
                }
            })

        if description:
            requests.append({
                "updateFormInfo": {
                    "info": {
                        "description": description
                    },
                    "updateMask": "description"
                }
            })

        # Execute batch update
        result = forms_service.forms().batchUpdate(
            formId=form_id,
            body={"requests": requests}
        ).execute()

        return [types.TextContent(type="text", text="Form updated successfully")]

    except HttpError as error:
        logger.error(f"Error updating form: {error}")
        return [types.TextContent(type="text", text=f"Error updating form: {error}")]

async def main():
    """Main entry point for the MCP server"""
    logger.info("Starting Google Forms MCP server...")

    # Initialize Forms client
    try:
        await init_forms_client()
    except Exception as e:
        logger.error(f"Failed to initialize Forms client: {e}")
        sys.exit(1)

    # Run the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Server running on stdio")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="google-forms-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
