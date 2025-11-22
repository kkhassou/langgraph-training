#!/usr/bin/env python3
"""
Google Calendar MCP Server

A Model Context Protocol server that provides Google Calendar integration capabilities.
This server allows AI assistants to interact with Google Calendar through standardized MCP tools.
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

# If modifying these scopes, delete the file token_calendar.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly',
          'https://www.googleapis.com/auth/calendar.events']

# Global Calendar service
calendar_service = None


async def init_calendar_client():
    """Initialize Google Calendar client with OAuth2 credentials"""
    global calendar_service

    if not GOOGLE_SDK_AVAILABLE:
        logger.warning("Google API client libraries not available")
        return False

    try:
        creds = None
        # The file token_calendar.json stores the user's access and refresh tokens
        token_path = os.getenv("GOOGLE_TOKEN_PATH", os.getenv("CALENDAR_TOKEN_PATH", "token_calendar.json"))
        credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", os.getenv("CALENDAR_CREDENTIALS_PATH", "credentials.json"))

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

        calendar_service = build('calendar', 'v3', credentials=creds)
        logger.info("Successfully connected to Google Calendar")
        return True

    except Exception as e:
        logger.error(f"Failed to connect to Google Calendar: {e}")
        calendar_service = None
        return False


async def list_events_tool(arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List events from Google Calendar"""
    if not calendar_service:
        raise Exception("Calendar client is not initialized. Please check your Google Calendar configuration.")

    try:
        calendar_id = arguments.get("calendar_id", "primary")
        max_results = arguments.get("max_results", 10)
        time_min = arguments.get("time_min")
        time_max = arguments.get("time_max")

        # Default to events from now onwards
        if not time_min:
            time_min = datetime.utcnow().isoformat() + 'Z'

        params = {
            'calendarId': calendar_id,
            'timeMin': time_min,
            'maxResults': max_results,
            'singleEvents': True,
            'orderBy': 'startTime'
        }

        if time_max:
            params['timeMax'] = time_max

        events_result = calendar_service.events().list(**params).execute()
        events = events_result.get('items', [])

        event_list = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))

            event_list.append({
                "id": event['id'],
                "summary": event.get('summary', 'No Title'),
                "start": start,
                "end": end,
                "description": event.get('description', ''),
                "location": event.get('location', ''),
                "attendees": [a.get('email') for a in event.get('attendees', [])]
            })

        return event_list

    except HttpError as error:
        logger.error(f"Calendar API error in list_events: {error}")
        raise Exception(f"Calendar API error: {str(error)}")


async def create_event_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new event in Google Calendar"""
    if not calendar_service:
        raise Exception("Calendar client is not initialized. Please check your Google Calendar configuration.")

    try:
        calendar_id = arguments.get("calendar_id", "primary")
        summary = arguments.get("summary")
        start_time = arguments.get("start_time")
        end_time = arguments.get("end_time")
        description = arguments.get("description", "")
        location = arguments.get("location", "")
        attendees = arguments.get("attendees", [])

        if not summary or not start_time or not end_time:
            raise ValueError("'summary', 'start_time', and 'end_time' are required")

        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'Asia/Tokyo',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'Asia/Tokyo',
            },
        }

        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]

        result = calendar_service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()

        return {
            "id": result.get('id'),
            "htmlLink": result.get('htmlLink'),
            "status": "created",
            "summary": result.get('summary')
        }

    except HttpError as error:
        logger.error(f"Calendar API error in create_event: {error}")
        raise Exception(f"Calendar API error: {str(error)}")


async def update_event_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing event in Google Calendar"""
    if not calendar_service:
        raise Exception("Calendar client is not initialized. Please check your Google Calendar configuration.")

    try:
        calendar_id = arguments.get("calendar_id", "primary")
        event_id = arguments.get("event_id")

        if not event_id:
            raise ValueError("'event_id' is required")

        # Get the existing event
        event = calendar_service.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()

        # Update fields if provided
        if arguments.get("summary"):
            event['summary'] = arguments.get("summary")
        if arguments.get("description"):
            event['description'] = arguments.get("description")
        if arguments.get("location"):
            event['location'] = arguments.get("location")
        if arguments.get("start_time"):
            event['start'] = {
                'dateTime': arguments.get("start_time"),
                'timeZone': 'Asia/Tokyo',
            }
        if arguments.get("end_time"):
            event['end'] = {
                'dateTime': arguments.get("end_time"),
                'timeZone': 'Asia/Tokyo',
            }

        result = calendar_service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event
        ).execute()

        return {
            "id": result.get('id'),
            "status": "updated",
            "summary": result.get('summary')
        }

    except HttpError as error:
        logger.error(f"Calendar API error in update_event: {error}")
        raise Exception(f"Calendar API error: {str(error)}")


async def delete_event_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Delete an event from Google Calendar"""
    if not calendar_service:
        raise Exception("Calendar client is not initialized. Please check your Google Calendar configuration.")

    try:
        calendar_id = arguments.get("calendar_id", "primary")
        event_id = arguments.get("event_id")

        if not event_id:
            raise ValueError("'event_id' is required")

        calendar_service.events().delete(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()

        return {
            "status": "deleted",
            "event_id": event_id
        }

    except HttpError as error:
        logger.error(f"Calendar API error in delete_event: {error}")
        raise Exception(f"Calendar API error: {str(error)}")


# Create the MCP server
app = Server("calendar-mcp-server")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available Google Calendar tools"""
    return [
        Tool(
            name="list_events",
            description="List events from Google Calendar",
            inputSchema={
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID (default: 'primary')",
                        "default": "primary"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of events to retrieve (default: 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "time_min": {
                        "type": "string",
                        "description": "Lower bound (ISO 8601 format, e.g., '2024-01-01T00:00:00Z')"
                    },
                    "time_max": {
                        "type": "string",
                        "description": "Upper bound (ISO 8601 format)"
                    }
                }
            }
        ),
        Tool(
            name="create_event",
            description="Create a new event in Google Calendar",
            inputSchema={
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID (default: 'primary')",
                        "default": "primary"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Event title/summary"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time (ISO 8601 format, e.g., '2024-01-01T10:00:00')"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time (ISO 8601 format)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Event description (optional)"
                    },
                    "location": {
                        "type": "string",
                        "description": "Event location (optional)"
                    },
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of attendee email addresses (optional)"
                    }
                },
                "required": ["summary", "start_time", "end_time"]
            }
        ),
        Tool(
            name="update_event",
            description="Update an existing event in Google Calendar",
            inputSchema={
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID (default: 'primary')",
                        "default": "primary"
                    },
                    "event_id": {
                        "type": "string",
                        "description": "Event ID to update"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Event title/summary (optional)"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time (ISO 8601 format, optional)"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time (ISO 8601 format, optional)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Event description (optional)"
                    },
                    "location": {
                        "type": "string",
                        "description": "Event location (optional)"
                    }
                },
                "required": ["event_id"]
            }
        ),
        Tool(
            name="delete_event",
            description="Delete an event from Google Calendar",
            inputSchema={
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID (default: 'primary')",
                        "default": "primary"
                    },
                    "event_id": {
                        "type": "string",
                        "description": "Event ID to delete"
                    }
                },
                "required": ["event_id"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls"""
    try:
        if name == "list_events":
            events = await list_events_tool(arguments)

            if not events:
                return [TextContent(type="text", text="No upcoming events found.")]

            event_text = f"Found {len(events)} event(s):\n\n"
            for event in events:
                event_text += f"📅 {event['summary']}\n"
                event_text += f"   Start: {event['start']}\n"
                event_text += f"   End: {event['end']}\n"
                if event['location']:
                    event_text += f"   Location: {event['location']}\n"
                if event['description']:
                    event_text += f"   Description: {event['description'][:100]}...\n"
                event_text += "\n"

            return [TextContent(type="text", text=event_text)]

        elif name == "create_event":
            result = await create_event_tool(arguments)
            summary = arguments.get("summary", "")
            start = arguments.get("start_time", "")

            return [
                TextContent(
                    type="text",
                    text=f"✅ Event created successfully\nTitle: {summary}\nStart: {start}\nLink: {result.get('htmlLink', 'N/A')}"
                )
            ]

        elif name == "update_event":
            result = await update_event_tool(arguments)

            return [
                TextContent(
                    type="text",
                    text=f"✅ Event updated successfully\nEvent ID: {result['id']}\nTitle: {result.get('summary', 'N/A')}"
                )
            ]

        elif name == "delete_event":
            result = await delete_event_tool(arguments)

            return [
                TextContent(
                    type="text",
                    text=f"✅ Event deleted successfully\nEvent ID: {result['event_id']}"
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
    # Initialize Calendar client
    await init_calendar_client()

    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
