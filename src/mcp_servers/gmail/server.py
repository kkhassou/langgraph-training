#!/usr/bin/env python3
"""
Gmail MCP Server

A Model Context Protocol server that provides Gmail integration capabilities.
This server allows AI assistants to interact with Gmail through standardized MCP tools.
"""

import asyncio
import os
import logging
from typing import Any, Dict, List, Optional, Sequence
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GMAIL_SDK_AVAILABLE = True
except ImportError:
    GMAIL_SDK_AVAILABLE = False
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

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/gmail.send']

# Global Gmail service
gmail_service = None


async def init_gmail_client():
    """Initialize Gmail client with OAuth2 credentials"""
    global gmail_service

    if not GMAIL_SDK_AVAILABLE:
        logger.warning("Google API client libraries not available")
        return False

    try:
        creds = None
        # The file token.json stores the user's access and refresh tokens
        token_path = os.getenv("GMAIL_TOKEN_PATH", "token.json")
        credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")

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

        gmail_service = build('gmail', 'v1', credentials=creds)
        logger.info("Successfully connected to Gmail")
        return True

    except Exception as e:
        logger.error(f"Failed to connect to Gmail: {e}")
        gmail_service = None
        return False


async def watch_inbox_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Set up Gmail push notifications for new emails"""
    if not gmail_service:
        raise Exception("Gmail client is not initialized. Please check your Gmail configuration.")

    try:
        topic_name = arguments.get("topic_name")
        if not topic_name:
            raise ValueError("topic_name parameter is required")

        request = {
            'labelIds': ['INBOX'],
            'topicName': topic_name
        }

        response = gmail_service.users().watch(userId='me', body=request).execute()

        return {
            "historyId": response.get("historyId"),
            "expiration": response.get("expiration"),
            "status": "watching"
        }

    except HttpError as error:
        logger.error(f"Gmail API error in watch_inbox: {error}")
        raise Exception(f"Gmail API error: {str(error)}")


async def get_messages_tool(arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get messages from Gmail inbox"""
    if not gmail_service:
        raise Exception("Gmail client is not initialized. Please check your Gmail configuration.")

    try:
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 10)

        # Get message list
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])

        detailed_messages = []
        for msg in messages:
            msg_data = gmail_service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()

            headers = msg_data.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown')

            # Get message body
            body = ""
            if 'parts' in msg_data['payload']:
                for part in msg_data['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        import base64
                        body = base64.urlsafe_b64decode(
                            part['body'].get('data', '')
                        ).decode('utf-8')
                        break
            elif 'body' in msg_data['payload']:
                import base64
                body = base64.urlsafe_b64decode(
                    msg_data['payload']['body'].get('data', '')
                ).decode('utf-8')

            detailed_messages.append({
                "id": msg['id'],
                "subject": subject,
                "from": sender,
                "date": date,
                "snippet": msg_data.get('snippet', ''),
                "body": body[:500] if body else msg_data.get('snippet', '')  # Limit body length
            })

        return detailed_messages

    except HttpError as error:
        logger.error(f"Gmail API error in get_messages: {error}")
        raise Exception(f"Gmail API error: {str(error)}")


async def send_message_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Send an email via Gmail"""
    if not gmail_service:
        raise Exception("Gmail client is not initialized. Please check your Gmail configuration.")

    try:
        to = arguments.get("to")
        subject = arguments.get("subject")
        body = arguments.get("body")

        if not to or not subject or not body:
            raise ValueError("'to', 'subject', and 'body' parameters are required")

        from email.mime.text import MIMEText
        import base64

        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        result = gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()

        return {
            "id": result.get('id'),
            "threadId": result.get('threadId'),
            "status": "sent"
        }

    except HttpError as error:
        logger.error(f"Gmail API error in send_message: {error}")
        raise Exception(f"Gmail API error: {str(error)}")


# Create the MCP server
app = Server("gmail-mcp-server")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available Gmail tools"""
    return [
        Tool(
            name="watch_inbox",
            description="Set up Gmail push notifications for new emails to a Pub/Sub topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic_name": {
                        "type": "string",
                        "description": "Google Cloud Pub/Sub topic name (e.g., 'projects/myproject/topics/gmail')"
                    }
                },
                "required": ["topic_name"]
            }
        ),
        Tool(
            name="get_messages",
            description="Get messages from Gmail inbox",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query (e.g., 'is:unread', 'from:example@gmail.com')",
                        "default": ""
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of messages to retrieve (default: 10, max: 100)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    }
                }
            }
        ),
        Tool(
            name="send_message",
            description="Send an email via Gmail",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient email address"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body text"
                    }
                },
                "required": ["to", "subject", "body"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls"""
    try:
        if name == "watch_inbox":
            result = await watch_inbox_tool(arguments)
            return [
                TextContent(
                    type="text",
                    text=f"✅ Gmail inbox watching started\nHistory ID: {result['historyId']}\nExpiration: {result['expiration']}"
                )
            ]

        elif name == "get_messages":
            messages = await get_messages_tool(arguments)
            query = arguments.get("query", "all messages")

            if not messages:
                return [TextContent(type="text", text=f"No messages found for query: {query}")]

            message_text = f"Found {len(messages)} message(s):\n\n"
            for msg in messages:
                message_text += f"📧 Subject: {msg['subject']}\n"
                message_text += f"   From: {msg['from']}\n"
                message_text += f"   Date: {msg['date']}\n"
                message_text += f"   Preview: {msg['snippet'][:100]}...\n\n"

            return [TextContent(type="text", text=message_text)]

        elif name == "send_message":
            result = await send_message_tool(arguments)
            to = arguments.get("to", "unknown")
            subject = arguments.get("subject", "")

            return [
                TextContent(
                    type="text",
                    text=f"✅ Email sent successfully\nTo: {to}\nSubject: {subject}\nMessage ID: {result['id']}"
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
    # Initialize Gmail client
    await init_gmail_client()

    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
