"""Google Calendar MCP Node - Handles Google Calendar operations via MCP server"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import logging

from src.services.mcp.google_calendar import CalendarMCPService
from src.nodes.base import BaseNode, NodeResult

logger = logging.getLogger(__name__)


class CalendarMCPInput(BaseModel):
    """Input schema for Google Calendar MCP node"""
    action: str = Field(..., description="Action to perform: list_events, create_event, update_event, delete_event")
    calendar_id: Optional[str] = Field("primary", description="Calendar ID (default: primary)")

    # For list_events
    max_results: Optional[int] = Field(10, description="Maximum number of events to retrieve")
    time_min: Optional[str] = Field(None, description="Lower bound (ISO 8601 format)")
    time_max: Optional[str] = Field(None, description="Upper bound (ISO 8601 format)")

    # For create_event and update_event
    event_id: Optional[str] = Field(None, description="Event ID (required for update/delete)")
    summary: Optional[str] = Field(None, description="Event title/summary")
    start_time: Optional[str] = Field(None, description="Start time (ISO 8601 format)")
    end_time: Optional[str] = Field(None, description="End time (ISO 8601 format)")
    description: Optional[str] = Field(None, description="Event description")
    location: Optional[str] = Field(None, description="Event location")
    attendees: Optional[List[str]] = Field(None, description="List of attendee email addresses")


class CalendarMCPNode(BaseNode):
    """Node for Google Calendar operations via MCP server"""

    def __init__(self):
        super().__init__("calendar-mcp")
        self.calendar_service = CalendarMCPService()

    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """Execute Google Calendar MCP node"""
        try:
            action = input_data.get("action")

            if action == "list_events":
                calendar_id = input_data.get("calendar_id", "primary")
                max_results = input_data.get("max_results", 10)
                time_min = input_data.get("time_min")
                time_max = input_data.get("time_max")

                result = await self.calendar_service.list_events(
                    calendar_id=calendar_id,
                    max_results=max_results,
                    time_min=time_min,
                    time_max=time_max
                )
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "list_events", "calendar_id": calendar_id}
                )

            elif action == "create_event":
                summary = input_data.get("summary")
                start_time = input_data.get("start_time")
                end_time = input_data.get("end_time")

                if not all([summary, start_time, end_time]):
                    raise ValueError("summary, start_time, and end_time are required for create_event action")

                result = await self.calendar_service.create_event(
                    calendar_id=input_data.get("calendar_id", "primary"),
                    summary=summary,
                    start_time=start_time,
                    end_time=end_time,
                    description=input_data.get("description", ""),
                    location=input_data.get("location", ""),
                    attendees=input_data.get("attendees")
                )
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "create_event", "summary": summary}
                )

            elif action == "update_event":
                event_id = input_data.get("event_id")
                if not event_id:
                    raise ValueError("event_id is required for update_event action")

                result = await self.calendar_service.update_event(
                    event_id=event_id,
                    calendar_id=input_data.get("calendar_id", "primary"),
                    summary=input_data.get("summary"),
                    start_time=input_data.get("start_time"),
                    end_time=input_data.get("end_time"),
                    description=input_data.get("description"),
                    location=input_data.get("location")
                )
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "update_event", "event_id": event_id}
                )

            elif action == "delete_event":
                event_id = input_data.get("event_id")
                if not event_id:
                    raise ValueError("event_id is required for delete_event action")

                result = await self.calendar_service.delete_event(
                    event_id=event_id,
                    calendar_id=input_data.get("calendar_id", "primary")
                )
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "delete_event", "event_id": event_id}
                )

            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Error in Calendar MCP node: {e}")
            return NodeResult(
                success=False,
                error=str(e),
                metadata={"action": input_data.get("action")}
            )

    async def cleanup(self):
        """Cleanup Calendar MCP resources"""
        try:
            await self.calendar_service.disconnect()
        except Exception as e:
            logger.error(f"Error during Calendar MCP cleanup: {e}")


# Create node instance
calendar_mcp_node = CalendarMCPNode()


async def calendar_mcp_node_handler(input_data: CalendarMCPInput) -> Dict[str, Any]:
    """Handler function for Google Calendar MCP node endpoint"""
    result = await calendar_mcp_node.execute(input_data.model_dump())
    return result.model_dump()
