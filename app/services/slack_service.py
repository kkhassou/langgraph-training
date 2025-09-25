from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from app.core.dependencies import validate_slack_token


class SlackService:
    """Service for Slack API interactions"""

    def __init__(self):
        self.token = validate_slack_token()
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

    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user information"""
        try:
            response = await self.client.users_info(user=user_id)
            user = response["user"]
            return {
                "id": user["id"],
                "name": user.get("name", ""),
                "real_name": user.get("real_name", ""),
                "display_name": user.get("profile", {}).get("display_name", "")
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