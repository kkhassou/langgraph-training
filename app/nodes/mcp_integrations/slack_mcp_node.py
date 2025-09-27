from typing import Dict, Any, List, Optional
from enum import Enum

from app.nodes.mcp_integrations.mcp_base import MCPBaseNode
from app.nodes.base_node import NodeState, NodeInput, NodeOutput


class SlackMCPActionType(str, Enum):
    GET_MESSAGES = "get_messages"
    POST_MESSAGE = "post_message"
    SEARCH_MESSAGES = "search_messages"
    GET_CHANNELS = "get_channels"
    GET_CHANNEL_INFO = "get_channel_info"
    GET_USER = "get_user"
    CREATE_CHANNEL = "create_channel"


class SlackMCPNode(MCPBaseNode):
    """Node for Slack operations using MCP server"""

    def __init__(self):
        super().__init__(
            name="slack_mcp_node",
            mcp_server_name="slack",
            description="Interact with Slack API via MCP server"
        )

    async def execute_mcp(self, state: NodeState) -> NodeState:
        """Execute Slack MCP operation"""
        action = state.data.get("action", SlackMCPActionType.GET_CHANNELS)

        if action == SlackMCPActionType.GET_CHANNELS:
            result = await self.call_mcp_tool("list_channels", {})
            if not result.get("isError"):
                channels_data = result.get("content", {})
                if isinstance(channels_data, str):
                    import ast
                    channels_data = ast.literal_eval(channels_data)

                channels = channels_data.get("channels", [])
                state.data["channels"] = channels
                state.messages.append(f"Retrieved {len(channels)} channels via MCP")

        elif action == SlackMCPActionType.GET_MESSAGES:
            channel_id = state.data.get("channel_id")
            if not channel_id:
                raise ValueError("channel_id is required for get_messages action")

            arguments = {
                "channel_id": channel_id,
                "limit": state.data.get("limit", 100),
                "days_back": state.data.get("days_back", 7)
            }

            result = await self.call_mcp_tool("get_messages", arguments)
            if not result.get("isError"):
                messages_data = result.get("content", {})
                if isinstance(messages_data, str):
                    import ast
                    messages_data = ast.literal_eval(messages_data)

                messages = messages_data.get("messages", [])
                state.data["messages"] = messages
                state.messages.append(f"Retrieved {len(messages)} messages from channel {channel_id} via MCP")

        elif action == SlackMCPActionType.POST_MESSAGE:
            channel_id = state.data.get("channel_id")
            text = state.data.get("text")
            if not channel_id or not text:
                raise ValueError("channel_id and text are required for post_message action")

            arguments = {
                "channel_id": channel_id,
                "text": text
            }
            thread_ts = state.data.get("thread_ts")
            if thread_ts:
                arguments["thread_ts"] = thread_ts

            result = await self.call_mcp_tool("post_message", arguments)
            if not result.get("isError"):
                post_data = result.get("content", {})
                if isinstance(post_data, str):
                    import ast
                    post_data = ast.literal_eval(post_data)

                state.data["post_result"] = post_data
                state.messages.append(f"Posted message to channel {channel_id} via MCP")

        elif action == SlackMCPActionType.SEARCH_MESSAGES:
            query = state.data.get("query")
            if not query:
                raise ValueError("query is required for search_messages action")

            arguments = {
                "query": query,
                "count": state.data.get("count", 20)
            }

            result = await self.call_mcp_tool("search_messages", arguments)
            if not result.get("isError"):
                search_data = result.get("content", {})
                if isinstance(search_data, str):
                    import ast
                    search_data = ast.literal_eval(search_data)

                messages = search_data.get("messages", [])
                state.data["search_results"] = messages
                state.messages.append(f"Found {len(messages)} messages matching query via MCP")

        elif action == SlackMCPActionType.GET_CHANNEL_INFO:
            channel_id = state.data.get("channel_id")
            if not channel_id:
                raise ValueError("channel_id is required for get_channel_info action")

            result = await self.call_mcp_tool("get_channel_info", {"channel_id": channel_id})
            if not result.get("isError"):
                channel_data = result.get("content", {})
                if isinstance(channel_data, str):
                    import ast
                    channel_data = ast.literal_eval(channel_data)

                state.data["channel_info"] = channel_data
                state.messages.append(f"Retrieved channel info for {channel_id} via MCP")

        elif action == SlackMCPActionType.GET_USER:
            user_id = state.data.get("user_id")
            if not user_id:
                raise ValueError("user_id is required for get_user action")

            result = await self.call_mcp_tool("get_user", {"user_id": user_id})
            if not result.get("isError"):
                user_data = result.get("content", {})
                if isinstance(user_data, str):
                    import ast
                    user_data = ast.literal_eval(user_data)

                state.data["user_info"] = user_data
                state.messages.append(f"Retrieved user info for {user_id} via MCP")

        elif action == SlackMCPActionType.CREATE_CHANNEL:
            name = state.data.get("name")
            if not name:
                raise ValueError("name is required for create_channel action")

            arguments = {
                "name": name,
                "is_private": state.data.get("is_private", False)
            }

            result = await self.call_mcp_tool("create_channel", arguments)
            if not result.get("isError"):
                channel_data = result.get("content", {})
                if isinstance(channel_data, str):
                    import ast
                    channel_data = ast.literal_eval(channel_data)

                state.data["created_channel"] = channel_data
                state.messages.append(f"Created channel '{name}' via MCP")

        # Handle MCP errors
        if result.get("isError"):
            error_content = result.get("content", "Unknown MCP error")
            state.data["error"] = f"MCP Slack error: {error_content}"

        state.metadata["node"] = self.name
        state.metadata["mcp_server"] = self.mcp_server_name
        return state


class SlackMCPInput(NodeInput):
    """Input model for Slack MCP node"""
    action: SlackMCPActionType
    channel_id: Optional[str] = None
    text: Optional[str] = None
    query: Optional[str] = None
    user_id: Optional[str] = None
    name: Optional[str] = None
    limit: int = 100
    days_back: int = 7
    count: int = 20
    is_private: bool = False


class SlackMCPOutput(NodeOutput):
    """Output model for Slack MCP node"""
    channels: List[Dict[str, Any]] = []
    messages: List[Dict[str, Any]] = []
    search_results: List[Dict[str, Any]] = []
    post_result: Optional[Dict[str, Any]] = None
    channel_info: Optional[Dict[str, Any]] = None
    user_info: Optional[Dict[str, Any]] = None
    created_channel: Optional[Dict[str, Any]] = None


async def slack_mcp_node_handler(input_data: SlackMCPInput) -> SlackMCPOutput:
    """Standalone handler for Slack MCP node API endpoint"""
    try:
        node = SlackMCPNode()
        state = NodeState()
        state.data.update({
            "action": input_data.action,
            "channel_id": input_data.channel_id,
            "text": input_data.text,
            "query": input_data.query,
            "user_id": input_data.user_id,
            "name": input_data.name,
            "limit": input_data.limit,
            "days_back": input_data.days_back,
            "count": input_data.count,
            "is_private": input_data.is_private,
        })

        result_state = await node.execute(state)

        if "error" in result_state.data:
            return SlackMCPOutput(
                output_text="",
                success=False,
                error_message=result_state.data["error"]
            )

        # Format output based on action
        output_text = ""
        if result_state.messages:
            output_text = result_state.messages[-1]

        return SlackMCPOutput(
            output_text=output_text,
            channels=result_state.data.get("channels", []),
            messages=result_state.data.get("messages", []),
            search_results=result_state.data.get("search_results", []),
            post_result=result_state.data.get("post_result"),
            channel_info=result_state.data.get("channel_info"),
            user_info=result_state.data.get("user_info"),
            created_channel=result_state.data.get("created_channel"),
            data=result_state.data
        )

    except Exception as e:
        return SlackMCPOutput(
            output_text="",
            success=False,
            error_message=str(e)
        )