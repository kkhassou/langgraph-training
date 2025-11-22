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
    
    Attributes:
        service: SlackMCPServiceインスタンス
    
    Example:
        >>> node = SlackNode()
        >>> state = NodeState()
        >>> state.data["action"] = SlackActionType.SEND_MESSAGE
        >>> state.data["channel"] = "C09HH9HTQJ2"
        >>> state.data["text"] = "Hello from LangGraph!"
        >>> result_state = await node.execute(state)
    """

    def __init__(self):
        super().__init__(
            name="slack_node",
            description="Interact with Slack API via MCP server"
        )
        self.service = SlackMCPService()

    async def execute(self, state: NodeState) -> NodeState:
        """Slack操作を実行
        
        Args:
            state: ノード状態
                - data["action"]: 実行するアクション (SlackActionType)
                - data["channel"]: チャンネルID（send_message, get_messagesで必須）
                - data["text"]: メッセージテキスト（send_messageで必須）
                - data["limit"]: 取得メッセージ数（get_messagesで使用）
                - data["days_back"]: 何日前まで遡るか（get_messagesで使用）
        
        Returns:
            NodeState: 実行結果を含む状態
                - data["channels"]: チャンネル一覧（get_channelsの場合）
                - data["messages"]: メッセージ一覧（get_messagesの場合）
                - data["sent_message"]: 送信メッセージ情報（send_messageの場合）
                - data["available_tools"]: 利用可能なツール一覧（list_toolsの場合）
                - data["error"]: エラーメッセージ（エラー時）
        """
        try:
            action = state.data.get("action", SlackActionType.SEND_MESSAGE)

            if action == SlackActionType.GET_CHANNELS:
                result = await self.service.get_channels()

                # Extract message from MCP response content
                channels = []
                content = result.get("content", [])
                if content and len(content) > 0:
                    text_content = content[0].get("text", "")
                    try:
                        # Parse the string representation of the dictionary
                        import ast
                        parsed_result = ast.literal_eval(text_content)
                        channels = parsed_result.get("channels", [])
                    except:
                        # Fallback: try to get channels from result directly
                        channels = result.get("channels", [])
                else:
                    channels = result.get("channels", [])
                
                state.data["channels"] = channels
                message = f"Retrieved {len(channels)} channels via MCP"
                state.messages.append(message)

            elif action == SlackActionType.SEND_MESSAGE:
                channel = state.data.get("channel")
                text = state.data.get("text")

                if not channel or not text:
                    raise ValueError("channel and text are required for send_message action")

                result = await self.service.send_message(channel, text)

                # Check if the result contains an error
                is_error = result.get("isError", False)
                
                if is_error:
                    # Extract error message from MCP response
                    content = result.get("content", [])
                    error_msg = content[0].get("text", "Unknown error") if content else "Unknown error"
                    raise Exception(f"Error executing send_message: {error_msg}")

                # Extract message info from MCP response
                message_info = result.get("message", {})
                state.data["sent_message"] = message_info

                # Extract message from MCP response
                content = result.get("content", [])
                if content and len(content) > 0:
                    message = content[0].get("text", f"Message sent to {channel} via MCP")
                else:
                    message = f"Message sent to {channel} via MCP"

                state.messages.append(message)

            elif action == SlackActionType.GET_MESSAGES:
                channel = state.data.get("channel")
                if not channel:
                    raise ValueError("channel is required for get_messages action")

                limit = state.data.get("limit", 10)
                days_back = state.data.get("days_back", 7)
                result = await self.service.get_messages(channel, limit, days_back)

                # Extract messages from MCP response
                messages = []
                content = result.get("content", [])
                if content and len(content) > 0:
                    text_content = content[0].get("text", "")
                    try:
                        # Parse the string representation of the dictionary
                        import ast
                        parsed_result = ast.literal_eval(text_content)
                        messages = parsed_result.get("messages", [])
                    except:
                        # Fallback: try to get messages directly from result
                        messages = result.get("messages", [])
                else:
                    messages = result.get("messages", [])

                state.data["messages"] = messages
                message = f"Retrieved {len(messages)} messages from {channel} via MCP"
                state.messages.append(message)

            elif action == SlackActionType.LIST_TOOLS:
                tools = await self.service.list_available_tools()
                state.data["available_tools"] = tools
                state.messages.append(f"Retrieved {len(tools)} available MCP tools")

            state.metadata["node"] = self.name
            state.metadata["mcp_mode"] = True
            return state

        except Exception as e:
            state.data["error"] = str(e)
            state.metadata["error_node"] = self.name
            state.metadata["mcp_mode"] = True
            return state

    async def cleanup(self):
        """MCPサービス接続のクリーンアップ"""
        if self.service:
            await self.service.disconnect()


class SlackInput(NodeInput):
    """Slackノードの入力スキーマ"""
    
    action: SlackActionType = Field(
        default=SlackActionType.SEND_MESSAGE,
        description="Slack action to perform (get_channels, send_message, get_messages, list_tools)"
    )
    channel: Optional[str] = Field(
        default="C09HH9HTQJ2",
        description="Slack channel ID (e.g., C09HH9HTQJ2)"
    )
    text: Optional[str] = Field(
        default="Hello from LangGraph Training API! 🚀",
        description="Message text to send (required for send_message action)"
    )
    limit: int = Field(
        default=10,
        description="Number of messages to retrieve (for get_messages action)"
    )


class SlackOutput(NodeOutput):
    """Slackノードの出力スキーマ"""
    
    channels: List[Dict[str, Any]] = []
    messages: List[Dict[str, Any]] = []
    sent_message: Optional[Dict[str, Any]] = None
    available_tools: List[Dict[str, Any]] = []


async def slack_node_handler(input_data: SlackInput) -> SlackOutput:
    """Slackノードのスタンドアロンハンドラー
    
    APIエンドポイントから直接呼び出される場合に使用します。
    
    Args:
        input_data: Slack操作の入力パラメータ
    
    Returns:
        SlackOutput: 実行結果
    
    Example:
        >>> input_data = SlackInput(
        ...     action=SlackActionType.SEND_MESSAGE,
        ...     channel="C09HH9HTQJ2",
        ...     text="Hello!"
        ... )
        >>> result = await slack_node_handler(input_data)
    """
    try:
        # For get_channels action, directly call the MCP service (known working approach)
        if input_data.action == SlackActionType.GET_CHANNELS:
            from src.mcp.slack.client import SlackMCPService
            
            service = SlackMCPService()
            try:
                await service.ensure_connected()
                result = await service.get_channels()
                
                # Parse the detailed response from MCP
                channels = []
                output_text = "Retrieved channels successfully"
                
                content = result.get("content", [])
                if content and len(content) > 0:
                    message = content[0].get("text", "")
                    output_text = message
                    
                    # Parse channel information from the detailed text
                    if "Found" in message and "channels" in message:
                        lines = message.split('\n')
                        for line in lines[1:]:  # Skip the first line with count
                            if line.strip().startswith('•'):
                                # Parse line like "• #general (CV16XK97C)"
                                parts = line.strip()[2:].split(' (')
                                if len(parts) == 2:
                                    name = parts[0].replace('#', '')
                                    channel_id = parts[1].replace(')', '')
                                    channels.append({
                                        "id": channel_id,
                                        "name": name,
                                        "is_private": False
                                    })
                
                return SlackOutput(
                    output_text=output_text,
                    channels=channels,
                    data={
                        "action": input_data.action,
                        "channel": input_data.channel,
                        "text": input_data.text,
                        "limit": input_data.limit,
                        "channels": channels
                    }
                )
                
            finally:
                await service.disconnect()
                
        # For get_messages action, directly call the MCP service 
        elif input_data.action == SlackActionType.GET_MESSAGES:
            from src.mcp.slack.client import SlackMCPService
            
            if not input_data.channel:
                return SlackOutput(
                    output_text="",
                    success=False,
                    error_message="channel parameter is required for get_messages action"
                )
            
            service = SlackMCPService()
            try:
                await service.ensure_connected()
                result = await service.get_messages(input_data.channel, input_data.limit)
                
                # Parse the detailed response from MCP
                messages = []
                output_text = "Retrieved messages successfully"
                
                content = result.get("content", [])
                if content and len(content) > 0:
                    message = content[0].get("text", "")
                    output_text = message
                    
                    # Parse message information from the detailed text
                    if "Messages from" in message:
                        lines = message.split('\n')
                        for line in lines[2:]:  # Skip the first two lines (header and empty line)
                            if line.strip() and line.startswith('['):
                                # Parse line like "[1759074927.512519] UV2GBFUQK: っっっっf"
                                try:
                                    parts = line.split('] ')
                                    if len(parts) >= 2:
                                        ts = parts[0][1:]  # Remove the opening bracket
                                        user_and_text = parts[1]
                                        if ': ' in user_and_text:
                                            user, text = user_and_text.split(': ', 1)
                                            messages.append({
                                                "ts": ts,
                                                "user": user,
                                                "text": text,
                                                "type": "message"
                                            })
                                except Exception:
                                    continue
                
                return SlackOutput(
                    output_text=output_text,
                    messages=messages,
                    data={
                        "action": input_data.action,
                        "channel": input_data.channel,
                        "text": input_data.text,
                        "limit": input_data.limit,
                        "messages": messages
                    }
                )
                
            finally:
                await service.disconnect()
        
        # For other actions, use the node-based approach
        node = SlackNode()
        state = NodeState()
        state.data.update({
            "action": input_data.action,
            "channel": input_data.channel,
            "text": input_data.text,
            "limit": input_data.limit,
        })

        result_state = await node.execute(state)

        # Cleanup
        await node.cleanup()

        if "error" in result_state.data:
            return SlackOutput(
                output_text="",
                success=False,
                error_message=result_state.data["error"]
            )

        # Format output based on action
        output_text = ""
        if result_state.messages:
            output_text = result_state.messages[-1]

        # Check if output_text indicates an error
        is_error = "Error" in output_text or "error" in output_text.lower()
        
        return SlackOutput(
            output_text=output_text,
            success=not is_error,
            error_message=output_text if is_error else None,
            channels=result_state.data.get("channels", []),
            messages=result_state.data.get("messages", []),
            sent_message=result_state.data.get("sent_message"),
            available_tools=result_state.data.get("available_tools", []),
            data=result_state.data
        )

    except Exception as e:
        return SlackOutput(
            output_text="",
            success=False,
            error_message=str(e)
        )

