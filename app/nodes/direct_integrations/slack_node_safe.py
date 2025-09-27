from typing import List, Dict, Any, Optional
from enum import Enum

from app.nodes.base_node import BaseNode, NodeState, NodeInput, NodeOutput
from app.services.direct_services.slack_service_safe import get_slack_service


class SlackActionType(str, Enum):
    GET_MESSAGES = "get_messages"
    POST_MESSAGE = "post_message"
    SEARCH_MESSAGES = "search_messages"
    GET_CHANNELS = "get_channels"


class SlackNodeSafe(BaseNode):
    """Safe node for Slack operations with dependency checking"""

    def __init__(self):
        super().__init__(
            name="slack_node_safe",
            description="Interact with Slack API for messages and channels (safe version)"
        )
        self.service = None

    def _get_service(self):
        """Get or create Slack service instance"""
        if self.service is None:
            self.service = get_slack_service()
        return self.service

    async def execute(self, state: NodeState) -> NodeState:
        """Execute Slack operation"""
        try:
            service = self._get_service()
            action = state.data.get("action", SlackActionType.GET_CHANNELS)

            if action == SlackActionType.GET_CHANNELS:
                channels = await service.get_channels()
                state.data["channels"] = channels
                state.messages.append(f"Retrieved {len(channels)} channels")

            elif action == SlackActionType.GET_MESSAGES:
                channel_id = state.data.get("channel_id")
                if not channel_id:
                    raise ValueError("channel_id is required for get_messages action")

                limit = state.data.get("limit", 100)
                days_back = state.data.get("days_back", 7)

                messages = await service.get_messages(channel_id, limit, days_back)
                state.data["messages"] = messages
                state.messages.append(f"Retrieved {len(messages)} messages from channel {channel_id}")

            elif action == SlackActionType.POST_MESSAGE:
                channel_id = state.data.get("channel_id")
                text = state.data.get("text")
                if not channel_id or not text:
                    raise ValueError("channel_id and text are required for post_message action")

                thread_ts = state.data.get("thread_ts")
                result = await service.post_message(channel_id, text, thread_ts)
                state.data["post_result"] = result
                state.messages.append(f"Posted message to channel {channel_id}")

            elif action == SlackActionType.SEARCH_MESSAGES:
                query = state.data.get("query")
                if not query:
                    raise ValueError("query is required for search_messages action")

                count = state.data.get("count", 20)
                messages = await service.search_messages(query, count)
                state.data["search_results"] = messages
                state.messages.append(f"Found {len(messages)} messages matching query: {query}")

            state.metadata["node"] = self.name
            return state

        except Exception as e:
            state.data["error"] = str(e)
            state.metadata["error_node"] = self.name
            return state


class SlackInputSafe(NodeInput):
    """Input model for safe Slack node"""
    action: SlackActionType
    channel_id: Optional[str] = None
    text: Optional[str] = None
    query: Optional[str] = None
    limit: int = 100
    days_back: int = 7
    count: int = 20
    thread_ts: Optional[str] = None


class SlackOutputSafe(NodeOutput):
    """Output model for safe Slack node"""
    channels: List[Dict[str, Any]] = []
    messages: List[Dict[str, Any]] = []
    search_results: List[Dict[str, Any]] = []
    post_result: Optional[Dict[str, Any]] = None


async def slack_node_safe_handler(input_data: SlackInputSafe) -> SlackOutputSafe:
    """Standalone handler for safe Slack node API endpoint"""
    try:
        node = SlackNodeSafe()
        state = NodeState()
        state.data.update({
            "action": input_data.action,
            "channel_id": input_data.channel_id,
            "text": input_data.text,
            "query": input_data.query,
            "limit": input_data.limit,
            "days_back": input_data.days_back,
            "count": input_data.count,
            "thread_ts": input_data.thread_ts,
        })

        result_state = await node.execute(state)

        if "error" in result_state.data:
            return SlackOutputSafe(
                output_text="",
                success=False,
                error_message=result_state.data["error"]
            )

        # Format output based on action
        output_text = ""
        if result_state.messages:
            output_text = result_state.messages[-1]

        return SlackOutputSafe(
            output_text=output_text,
            channels=result_state.data.get("channels", []),
            messages=result_state.data.get("messages", []),
            search_results=result_state.data.get("search_results", []),
            post_result=result_state.data.get("post_result"),
            data=result_state.data
        )

    except Exception as e:
        return SlackOutputSafe(
            output_text="",
            success=False,
            error_message=str(e)
        )