"""Slack Integration Node

Slackとの統合を行うノード実装。
MCP (Model Context Protocol) サーバーを介してSlack APIと通信します。
"""

from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import Field

from src.nodes.base import BaseNode, NodeState, NodeInput, NodeOutput
from src.mcp.slack.client import SlackMCPService


class SlackActionType(str, Enum):
    """Slackアクション種別"""
    GET_CHANNELS = "get_channels"
    SEND_MESSAGE = "send_message"
    GET_MESSAGES = "get_messages"
    LIST_TOOLS = "list_tools"


class SlackNode(BaseNode):
    """Slack統合ノード
    
    MCPサーバーを介してSlack APIと通信し、以下の機能を提供します：
    - チャンネル一覧の取得
    - メッセージ送信
    - メッセージ取得
    - 利用可能なツールの一覧取得
    
    State入力:
        - data["action"]: 実行するアクション
        - data["channel"]: チャンネルID
        - data["text"]: メッセージテキスト
    
    State出力:
        - data["sent_message"]: 送信メッセージ情報
        - data["messages"]: メッセージ一覧
        - data["channels"]: チャンネル一覧
    """

    def __init__(self):
        super().__init__(
            name="slack_node",
            description="Interact with Slack API via MCP server"
        )
        self.service = SlackMCPService()

    async def execute(self, state: NodeState) -> NodeState:
        """Slack操作を実行"""
        try:
            action = state.data.get("action", SlackActionType.SEND_MESSAGE)

            if action == SlackActionType.GET_CHANNELS:
                result = await self.service.get_channels()
                channels = result.get("channels", [])
                # Fallback for content parsing logic if needed (simplified here)
                if not channels and "content" in result:
                     # logic to parse content if channels key is missing
                     pass

                state.data["channels"] = channels
                state.messages.append(f"Retrieved {len(channels)} channels")

            elif action == SlackActionType.SEND_MESSAGE:
                channel = state.data.get("channel")
                text = state.data.get("text")
                if not channel or not text:
                    raise ValueError("channel and text are required")

                result = await self.service.send_message(channel, text)
                state.data["sent_message"] = result
                state.messages.append(f"Message sent to {channel}")

            elif action == SlackActionType.GET_MESSAGES:
                channel = state.data.get("channel")
                limit = state.data.get("limit", 10)
                result = await self.service.get_messages(channel, limit)
                state.data["messages"] = result.get("messages", [])
                state.messages.append(f"Retrieved messages from {channel}")

            state.metadata["node"] = self.name
            state.metadata["mcp_mode"] = True
            return state

        except Exception as e:
            state.data["error"] = str(e)
            state.metadata["error_node"] = self.name
            return state

    async def cleanup(self):
        """MCPサービス接続のクリーンアップ"""
        if self.service:
            await self.service.disconnect()


class SlackInput(NodeInput):
    """Slackノードの入力スキーマ"""
    action: SlackActionType = SlackActionType.SEND_MESSAGE
    channel: Optional[str] = "C09HH9HTQJ2"
    text: Optional[str] = "Hello from LangGraph!"
    limit: int = 10


class SlackOutput(NodeOutput):
    """Slackノードの出力スキーマ"""
    channels: List[Dict[str, Any]] = []
    messages: List[Dict[str, Any]] = []
    sent_message: Optional[Dict[str, Any]] = None
    available_tools: List[Dict[str, Any]] = []


async def slack_node_handler(input_data: SlackInput) -> SlackOutput:
    """Slackノードのスタンドアロンハンドラー"""
    node = SlackNode()
    try:
        state = NodeState()
        state.data = {
            "action": input_data.action,
            "channel": input_data.channel,
            "text": input_data.text,
            "limit": input_data.limit
        }

        result_state = await node.execute(state)
        await node.cleanup()

        if "error" in result_state.data:
            return SlackOutput(
                output_text="",
                success=False,
                error_message=result_state.data["error"]
            )

        return SlackOutput(
            output_text=result_state.messages[-1] if result_state.messages else "",
            success=True,
            channels=result_state.data.get("channels", []),
            messages=result_state.data.get("messages", []),
            sent_message=result_state.data.get("sent_message"),
            data=result_state.data
        )
    except Exception as e:
        await node.cleanup()
        return SlackOutput(output_text="", success=False, error_message=str(e))
