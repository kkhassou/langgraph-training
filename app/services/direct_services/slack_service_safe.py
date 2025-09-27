from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

try:
    from slack_sdk.web.async_client import AsyncWebClient
    from slack_sdk.errors import SlackApiError
    SLACK_SDK_AVAILABLE = True
except ImportError:
    SLACK_SDK_AVAILABLE = False
    SlackApiError = Exception

from app.core.dependencies import validate_slack_token_safe


class SlackServiceSafe:
    """Safe service for Slack API interactions with dependency checking"""

    def __init__(self):
        if not SLACK_SDK_AVAILABLE:
            raise ImportError("slack-sdk is not installed. Please run: pip install slack-sdk")

        self.token = validate_slack_token_safe()
        self.client = AsyncWebClient(token=self.token)

    async def get_channels(self) -> List[Dict[str, Any]]:
        """Get list of channels"""
        try:
            response = await self.client.conversations_list(
                types="public_channel,private_channel"
            )
            return response["channels"]
        except SlackApiError as e:
            raise Exception(f"Slack API error: {e.response['error']}")

    async def get_messages(
        self,
        channel_id: str,
        limit: int = 100,
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """Get messages from a channel"""
        try:
            # Calculate timestamp for days back
            oldest_timestamp = (
                datetime.now() - timedelta(days=days_back)
            ).timestamp()

            response = await self.client.conversations_history(
                channel=channel_id,
                limit=limit,
                oldest=oldest_timestamp
            )

            messages = []
            for message in response["messages"]:
                # Skip bot messages and system messages
                if message.get("subtype") in ["bot_message", "channel_join", "channel_leave"]:
                    continue

                messages.append({
                    "text": message.get("text", ""),
                    "user": message.get("user", "unknown"),
                    "timestamp": message.get("ts", ""),
                    "thread_ts": message.get("thread_ts"),
                })

            return messages

        except SlackApiError as e:
            raise Exception(f"Slack API error: {e.response['error']}")

    async def post_message(
        self,
        channel_id: str,
        text: str,
        thread_ts: Optional[str] = None
    ) -> Dict[str, Any]:
        """Post a message to a channel"""
        try:
            response = await self.client.chat_postMessage(
                channel=channel_id,
                text=text,
                thread_ts=thread_ts
            )

            return {
                "ts": response["ts"],
                "channel": response["channel"],
                "message": response["message"]
            }

        except SlackApiError as e:
            raise Exception(f"Slack API error: {e.response['error']}")

    async def search_messages(
        self,
        query: str,
        count: int = 20
    ) -> List[Dict[str, Any]]:
        """Search messages across workspace"""
        try:
            response = await self.client.search_messages(
                query=query,
                count=count
            )

            messages = []
            for match in response["messages"]["matches"]:
                messages.append({
                    "text": match.get("text", ""),
                    "user": match.get("user", "unknown"),
                    "channel": match.get("channel", {}).get("id", ""),
                    "timestamp": match.get("ts", ""),
                })

            return messages

        except SlackApiError as e:
            raise Exception(f"Slack API error: {e.response['error']}")


class SlackServiceMock:
    """Mock service for when Slack SDK is not available"""

    def __init__(self):
        logger.warning("Using mock Slack service - slack-sdk not installed")

    async def get_channels(self) -> List[Dict[str, Any]]:
        return [
            {"id": "C1234567890", "name": "general", "is_private": False},
            {"id": "C0987654321", "name": "random", "is_private": False},
        ]

    async def get_messages(self, channel_id: str, limit: int = 100, days_back: int = 7) -> List[Dict[str, Any]]:
        return [
            {"text": "This is a mock message", "user": "U1234567890", "timestamp": "1234567890.123456"},
            {"text": "Another mock message", "user": "U0987654321", "timestamp": "1234567891.123456"},
        ]

    async def post_message(self, channel_id: str, text: str, thread_ts: Optional[str] = None) -> Dict[str, Any]:
        return {
            "ts": "1234567892.123456",
            "channel": channel_id,
            "message": {"text": text}
        }

    async def search_messages(self, query: str, count: int = 20) -> List[Dict[str, Any]]:
        return [
            {"text": f"Mock search result for: {query}", "user": "U1234567890", "channel": "C1234567890", "timestamp": "1234567893.123456"}
        ]


def get_slack_service():
    """Get Slack service instance (real or mock)"""
    if SLACK_SDK_AVAILABLE:
        try:
            return SlackServiceSafe()
        except Exception:
            logger.warning("Failed to initialize real Slack service, using mock")
            return SlackServiceMock()
    else:
        return SlackServiceMock()