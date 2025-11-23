"""Slack MCP Service - Slack操作のヘルパー関数群"""

from typing import Dict, Any, List, Optional
import logging

from src.mcp.slack.client import SlackMCPClient
from .base import BaseMCPService

logger = logging.getLogger(__name__)


class SlackService(BaseMCPService):
    """Slack MCP サービス"""
    
    def __init__(self):
        super().__init__("slack")
    
    async def initialize(self):
        """Slackクライアントの初期化"""
        if self._client is None:
            self._client = SlackMCPClient()
            await self._client.__aenter__()
            logger.info("Slack MCP client initialized")
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Slackツールを呼び出し
        
        Args:
            tool_name: ツール名（list_channels, post_message など）
            arguments: ツールの引数
        
        Returns:
            ツールの実行結果
        """
        await self._ensure_initialized()
        result = await self._client.call_tool(tool_name, arguments)
        return result
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """利用可能なSlackツールのリストを取得"""
        await self._ensure_initialized()
        tools = await self._client.list_tools()
        return tools.tools if hasattr(tools, 'tools') else []
    
    # ============================================
    # 便利なヘルパーメソッド
    # ============================================
    
    async def send_message(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Slackメッセージを送信
        
        Args:
            channel: チャンネルID（例: C09HH9HTQJ2）
            text: メッセージテキスト
            thread_ts: スレッドのタイムスタンプ（スレッド返信の場合）
        
        Returns:
            送信結果
        
        Example:
            >>> result = await SlackService().send_message(
            ...     channel="C09HH9HTQJ2",
            ...     text="Hello from Service Layer!"
            ... )
        """
        arguments = {
            "channel": channel,
            "text": text
        }
        if thread_ts:
            arguments["thread_ts"] = thread_ts
        
        logger.info(f"Sending message to channel {channel}")
        return await self.call_tool("post_message", arguments)
    
    async def get_channels(self) -> List[Dict[str, Any]]:
        """
        Slackチャンネルのリストを取得
        
        Returns:
            チャンネルのリスト
        
        Example:
            >>> channels = await SlackService().get_channels()
            >>> for ch in channels:
            ...     print(f"{ch['name']}: {ch['id']}")
        """
        logger.info("Fetching Slack channels")
        result = await self.call_tool("list_channels", {})
        
        # 結果をパース
        channels = []
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and item.get("type") == "text":
                    # テキストをパースしてチャンネル情報を抽出
                    text = item.get("text", "")
                    # 簡易的なパース（実際の実装に合わせて調整）
                    channels.append({"text": text})
        
        return channels
    
    async def get_messages(
        self,
        channel: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        チャンネルのメッセージを取得
        
        Args:
            channel: チャンネルID
            limit: 取得するメッセージ数
        
        Returns:
            メッセージのリスト
        
        Example:
            >>> messages = await SlackService().get_messages(
            ...     channel="C09HH9HTQJ2",
            ...     limit=5
            ... )
        """
        logger.info(f"Fetching messages from channel {channel}")
        return await self.call_tool("get_channel_messages", {
            "channel": channel,
            "limit": limit
        })
    
    async def add_reaction(
        self,
        channel: str,
        timestamp: str,
        reaction: str
    ) -> Dict[str, Any]:
        """
        メッセージにリアクションを追加
        
        Args:
            channel: チャンネルID
            timestamp: メッセージのタイムスタンプ
            reaction: リアクション名（例: thumbsup, tada）
        
        Returns:
            実行結果
        """
        logger.info(f"Adding reaction '{reaction}' to message")
        return await self.call_tool("add_reaction", {
            "channel": channel,
            "timestamp": timestamp,
            "name": reaction
        })
    
    async def close(self):
        """クライアントをクローズ"""
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None
            logger.info("Slack MCP client closed")


# グローバルインスタンス（シングルトンパターン）
_slack_service_instance: Optional[SlackService] = None


async def get_slack_service() -> SlackService:
    """Slackサービスのシングルトンインスタンスを取得"""
    global _slack_service_instance
    if _slack_service_instance is None:
        _slack_service_instance = SlackService()
        await _slack_service_instance.initialize()
    return _slack_service_instance


# 便利な関数エイリアス
async def send_slack_message(channel: str, text: str, **kwargs) -> Dict[str, Any]:
    """Slackメッセージ送信のエイリアス"""
    service = await get_slack_service()
    return await service.send_message(channel, text, **kwargs)


async def get_slack_channels() -> List[Dict[str, Any]]:
    """Slackチャンネル取得のエイリアス"""
    service = await get_slack_service()
    return await service.get_channels()

