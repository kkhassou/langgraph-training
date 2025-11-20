"""Google Apps Script MCP Server - Provides tools to interact with Google Apps Script API

This server exposes tools for:
- Creating Apps Script projects
- Getting project content
- Updating project content
- Running Apps Script functions
- Managing project deployments
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

# Google Apps Script API scopes
SCOPES = [
    'https://www.googleapis.com/auth/script.projects',
    'https://www.googleapis.com/auth/script.deployments',
    'https://www.googleapis.com/auth/drive.file'
]

# Global Apps Script service
script_service = None

async def init_script_client():
    """Initialize Google Apps Script API client"""
    global script_service

    try:
        # Get token and credentials paths from environment
        token_path = os.getenv(
            "GOOGLE_TOKEN_PATH",
            os.getenv("SCRIPT_TOKEN_PATH", "secrets/google_token.json")
        )
        credentials_path = os.getenv(
            "GOOGLE_CREDENTIALS_PATH",
            os.getenv("SCRIPT_CREDENTIALS_PATH", "secrets/google_credentials.json")
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

        # Build Apps Script service
        script_service = build('script', 'v1', credentials=creds)
        logger.info("Google Apps Script client initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Apps Script client: {e}")
        raise

# Create MCP server instance
server = Server("google-apps-script-mcp")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Google Apps Script tools"""
    return [
        types.Tool(
            name="create_project",
            description="Create a new Apps Script project",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Project title"
                    }
                },
                "required": ["title"]
            }
        ),
        types.Tool(
            name="get_project",
            description="Get Apps Script project content",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_id": {
                        "type": "string",
                        "description": "Script project ID"
                    }
                },
                "required": ["script_id"]
            }
        ),
        types.Tool(
            name="update_project",
            description="Update Apps Script project content",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_id": {
                        "type": "string",
                        "description": "Script project ID"
                    },
                    "file_name": {
                        "type": "string",
                        "description": "File name (e.g., 'Code.gs')"
                    },
                    "file_type": {
                        "type": "string",
                        "description": "File type: SERVER_JS, HTML, JSON"
                    },
                    "source": {
                        "type": "string",
                        "description": "File source code"
                    }
                },
                "required": ["script_id", "file_name", "file_type", "source"]
            }
        ),
        types.Tool(
            name="run_function",
            description="Run a function in Apps Script project",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_id": {
                        "type": "string",
                        "description": "Script project ID"
                    },
                    "function_name": {
                        "type": "string",
                        "description": "Function name to execute"
                    },
                    "parameters": {
                        "type": "array",
                        "description": "Function parameters (optional)",
                        "items": {}
                    }
                },
                "required": ["script_id", "function_name"]
            }
        ),
        types.Tool(
            name="list_deployments",
            description="List deployments of an Apps Script project",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_id": {
                        "type": "string",
                        "description": "Script project ID"
                    }
                },
                "required": ["script_id"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests"""

    if not script_service:
        await init_script_client()

    try:
        if name == "create_project":
            return await create_project_tool(arguments or {})
        elif name == "get_project":
            return await get_project_tool(arguments or {})
        elif name == "update_project":
            return await update_project_tool(arguments or {})
        elif name == "run_function":
            return await run_function_tool(arguments or {})
        elif name == "list_deployments":
            return await list_deployments_tool(arguments or {})
        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

# async def create_project_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
#     """Create a new Apps Script project"""
#     title = arguments.get("title", "Untitled Project")

#     try:
#         # Create project body - just title for creation
#         project = {
#             "title": title
#         }

#         # Create the project
#         result = script_service.projects().create(body=project).execute()

#         script_id = result.get("scriptId")
#         project_title = result.get("title")

#         # Now update it with initial code
#         initial_content = {
#             "files": [
#                 {
#                     "name": "Code",
#                     "type": "SERVER_JS",
#                     "source": "function myFunction() {\n  Logger.log('Hello, Apps Script!');\n}"
#                 }
#             ]
#         }

#         script_service.projects().updateContent(
#             scriptId=script_id,
#             body=initial_content
#         ).execute()

#         response_text = f"Apps Script project created successfully!\n"
#         response_text += f"Script ID: {script_id}\n"
#         response_text += f"Title: {project_title}\n"
#         response_text += f"Edit URL: https://script.google.com/d/{script_id}/edit"

#         return [types.TextContent(type="text", text=response_text)]

#     except HttpError as error:
#         logger.error(f"Error creating project: {error}")
#         return [types.TextContent(type="text", text=f"Error creating project: {error}")]
import time
from googleapiclient.errors import HttpError
from typing import Dict, Any, List
from mcp import types

async def create_project_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Create a new Apps Script project (fixed version with manifest + retry)"""
    title = arguments.get("title", "Untitled Project")

    try:
        # 1️⃣ Create empty project
        project_body = {"title": title}
        result = script_service.projects().create(body=project_body).execute()

        script_id = result.get("scriptId")
        project_title = result.get("title")

        # 2️⃣ Wait a bit for Google to propagate the new project
        time.sleep(2)

        # 3️⃣ Prepare default files (must include manifest 'appsscript')
        initial_content = {
            "files": [
                {
                    "name": "appsscript",
                    "type": "JSON",
                    "source": '{ "timeZone": "Asia/Tokyo", "exceptionLogging": "STACKDRIVER" }'
                },
                {
                    "name": "Code",
                    "type": "SERVER_JS",
                    "source": "function myFunction() {\n  Logger.log('Hello, Apps Script!');\n}"
                }
            ]
        }

        # 4️⃣ Try updating content, with retry if manifest not ready
        try:
            script_service.projects().updateContent(
                scriptId=script_id,
                body=initial_content
            ).execute()
        except HttpError as e:
            if "must include a manifest" in str(e):
                time.sleep(3)
                script_service.projects().updateContent(
                    scriptId=script_id,
                    body=initial_content
                ).execute()
            else:
                raise

        # 5️⃣ Success response
        response_text = (
            f"✅ Apps Script project created successfully!\n"
            f"Script ID: {script_id}\n"
            f"Title: {project_title}\n"
            f"Edit URL: https://script.google.com/d/{script_id}/edit"
        )

        return [types.TextContent(type="text", text=response_text)]

    except HttpError as error:
        logger.error(f"Error creating project: {error}")
        return [types.TextContent(type="text", text=f"Error creating project: {error}")]    

async def get_project_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Get Apps Script project content"""
    script_id = arguments.get("script_id")

    if not script_id:
        return [types.TextContent(type="text", text="Error: script_id is required")]

    try:
        result = script_service.projects().getContent(scriptId=script_id).execute()

        title = result.get("scriptId", "Unknown")
        files = result.get("files", [])

        response_text = f"Project ID: {title}\n\n"
        response_text += f"Files ({len(files)}):\n\n"

        for file_obj in files:
            file_name = file_obj.get("name")
            file_type = file_obj.get("type")
            source = file_obj.get("source", "")

            response_text += f"--- {file_name} ({file_type}) ---\n"
            response_text += f"{source}\n\n"

        return [types.TextContent(type="text", text=response_text)]

    except HttpError as error:
        logger.error(f"Error getting project: {error}")
        return [types.TextContent(type="text", text=f"Error getting project: {error}")]

async def update_project_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Update Apps Script project content"""
    script_id = arguments.get("script_id")
    file_name = arguments.get("file_name")
    file_type = arguments.get("file_type", "SERVER_JS")
    source = arguments.get("source")

    if not script_id or not file_name or not source:
        return [types.TextContent(type="text", text="Error: script_id, file_name, and source are required")]

    try:
        # Get current project content
        current_content = script_service.projects().getContent(scriptId=script_id).execute()

        # Find and update the file, or add new file
        files = current_content.get("files", [])
        file_found = False

        for file_obj in files:
            if file_obj.get("name") == file_name:
                file_obj["source"] = source
                file_obj["type"] = file_type
                file_found = True
                break

        if not file_found:
            files.append({
                "name": file_name,
                "type": file_type,
                "source": source
            })

        # Update the project
        updated_content = {
            "files": files
        }

        result = script_service.projects().updateContent(
            scriptId=script_id,
            body=updated_content
        ).execute()

        return [types.TextContent(type="text", text=f"Project updated successfully. File '{file_name}' has been updated.")]

    except HttpError as error:
        logger.error(f"Error updating project: {error}")
        return [types.TextContent(type="text", text=f"Error updating project: {error}")]

async def run_function_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Run a function in Apps Script project"""
    script_id = arguments.get("script_id")
    function_name = arguments.get("function_name")
    parameters = arguments.get("parameters", [])

    if not script_id or not function_name:
        return [types.TextContent(type="text", text="Error: script_id and function_name are required")]

    try:
        # Create execution request
        request = {
            "function": function_name,
            "parameters": parameters
        }

        # Run the function
        result = script_service.scripts().run(
            scriptId=script_id,
            body=request
        ).execute()

        if "error" in result:
            error_message = result["error"].get("message", "Unknown error")
            return [types.TextContent(type="text", text=f"Function execution failed: {error_message}")]

        response = result.get("response", {})
        result_value = response.get("result")

        response_text = f"Function '{function_name}' executed successfully!\n\n"
        response_text += f"Result:\n{json.dumps(result_value, indent=2)}"

        return [types.TextContent(type="text", text=response_text)]

    except HttpError as error:
        logger.error(f"Error running function: {error}")
        return [types.TextContent(type="text", text=f"Error running function: {error}")]

async def list_deployments_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """List deployments of an Apps Script project"""
    script_id = arguments.get("script_id")

    if not script_id:
        return [types.TextContent(type="text", text="Error: script_id is required")]

    try:
        result = script_service.projects().deployments().list(scriptId=script_id).execute()

        deployments = result.get("deployments", [])

        if not deployments:
            return [types.TextContent(type="text", text="No deployments found for this project.")]

        response_text = f"Found {len(deployments)} deployment(s):\n\n"

        for idx, deployment in enumerate(deployments, 1):
            deployment_id = deployment.get("deploymentId")
            config = deployment.get("deploymentConfig", {})
            description = config.get("description", "No description")
            version_number = config.get("versionNumber", "HEAD")

            response_text += f"{idx}. Deployment ID: {deployment_id}\n"
            response_text += f"   Description: {description}\n"
            response_text += f"   Version: {version_number}\n\n"

        return [types.TextContent(type="text", text=response_text)]

    except HttpError as error:
        logger.error(f"Error listing deployments: {error}")
        return [types.TextContent(type="text", text=f"Error listing deployments: {error}")]

async def main():
    """Main entry point for the MCP server"""
    logger.info("Starting Google Apps Script MCP server...")

    # Initialize Apps Script client
    try:
        await init_script_client()
    except Exception as e:
        logger.error(f"Failed to initialize Apps Script client: {e}")
        sys.exit(1)

    # Run the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Server running on stdio")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="google-apps-script-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
