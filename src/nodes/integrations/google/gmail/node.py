"""Gmail Integration Node

Gmailとの統合を行うノード実装。
MCP (Model Context Protocol) サーバーを介してGmail APIと通信します。
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from src.mcp.google.gmail.client import GmailMCPService
from src.nodes.base import BaseNode, NodeResult

logger = logging.getLogger(__name__)


class GmailInput(BaseModel):
    """Gmailノードの入力スキーマ"""
    
    action: str = Field(
        ...,
        description="Action to perform: watch_inbox, get_messages, send_message"
    )
    topic_name: Optional[str] = Field(None, description="Pub/Sub topic name for watch_inbox")
    query: Optional[str] = Field("", description="Gmail search query for get_messages")
    max_results: Optional[int] = Field(10, description="Maximum number of messages to retrieve")
    to: Optional[str] = Field(None, description="Recipient email for send_message")
    subject: Optional[str] = Field(None, description="Email subject for send_message")
    body: Optional[str] = Field(None, description="Email body for send_message")


class GmailNode(BaseNode):
    """Gmail統合ノード
    
    MCPサーバーを介してGmail APIと通信し、以下の機能を提供します：
    - 受信トレイの監視設定
    - メッセージの検索・取得
    - メッセージの送信
    
    Attributes:
        gmail_service: GmailMCPServiceインスタンス
    
    Example:
        >>> node = GmailNode()
        >>> input_data = {
        ...     "action": "send_message",
        ...     "to": "recipient@example.com",
        ...     "subject": "Test",
        ...     "body": "Hello"
        ... }
        >>> result = await node.execute(input_data)
    """

    def __init__(self):
        super().__init__("gmail_node")
        self.gmail_service = GmailMCPService()

    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """Gmail操作を実行
        
        Args:
            input_data: 入力データ
                - action: 実行するアクション
                - その他アクション固有のパラメータ
        
        Returns:
            NodeResult: 実行結果
        """
        try:
            action = input_data.get("action")

            if action == "watch_inbox":
                topic_name = input_data.get("topic_name")
                if not topic_name:
                    raise ValueError("topic_name is required for watch_inbox action")

                result = await self.gmail_service.watch_inbox(topic_name)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "watch_inbox", "topic": topic_name}
                )

            elif action == "get_messages":
                query = input_data.get("query", "")
                max_results = input_data.get("max_results", 10)

                result = await self.gmail_service.get_messages(query, max_results)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "get_messages", "query": query, "max_results": max_results}
                )

            elif action == "send_message":
                to = input_data.get("to")
                subject = input_data.get("subject")
                body = input_data.get("body")

                if not all([to, subject, body]):
                    raise ValueError("to, subject, and body are required for send_message action")

                result = await self.gmail_service.send_message(to, subject, body)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "send_message", "to": to, "subject": subject}
                )

            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Error in Gmail node: {e}")
            return NodeResult(
                success=False,
                error=str(e),
                metadata={"action": input_data.get("action")}
            )

    async def cleanup(self):
        """Gmailサービス接続のクリーンアップ"""
        try:
            await self.gmail_service.disconnect()
        except Exception as e:
            logger.error(f"Error during Gmail cleanup: {e}")


# Create node instance
gmail_node = GmailNode()


async def gmail_node_handler(input_data: GmailInput) -> Dict[str, Any]:
    """Gmailノードのスタンドアロンハンドラー
    
    APIエンドポイントから直接呼び出される場合に使用します。
    
    Args:
        input_data: Gmail操作の入力パラメータ
    
    Returns:
        Dict[str, Any]: 実行結果
    """
    result = await gmail_node.execute(input_data.model_dump())
    return result.model_dump()

