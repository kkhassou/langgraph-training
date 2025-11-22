"""Gmail MCP Service - Gmail操作のヘルパー関数群"""

from typing import Dict, Any, List, Optional
import logging

from src.mcp.google.gmail.client import GmailMCPClient
from ..base import BaseMCPService

logger = logging.getLogger(__name__)


class GmailService(BaseMCPService):
    """Gmail MCP サービス"""
    
    def __init__(self):
        super().__init__("gmail")
    
    async def initialize(self):
        """Gmailクライアントの初期化"""
        if self._client is None:
            self._client = GmailMCPClient()
            await self._client.__aenter__()
            logger.info("Gmail MCP client initialized")
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Gmailツールを呼び出し"""
        await self._ensure_initialized()
        result = await self._client.call_tool(tool_name, arguments)
        return result
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """利用可能なGmailツールのリストを取得"""
        await self._ensure_initialized()
        tools = await self._client.list_tools()
        return tools.tools if hasattr(tools, 'tools') else []
    
    # ============================================
    # 便利なヘルパーメソッド
    # ============================================
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        メールを送信
        
        Args:
            to: 宛先
            subject: 件名
            body: 本文
            cc: CC
            bcc: BCC
        
        Returns:
            送信結果
        """
        arguments = {
            "to": to,
            "subject": subject,
            "body": body
        }
        if cc:
            arguments["cc"] = cc
        if bcc:
            arguments["bcc"] = bcc
        
        logger.info(f"Sending email to {to}")
        return await self.call_tool("send_email", arguments)
    
    async def list_messages(
        self,
        query: Optional[str] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        メールリストを取得
        
        Args:
            query: 検索クエリ
            max_results: 最大取得件数
        
        Returns:
            メールのリスト
        """
        arguments = {"max_results": max_results}
        if query:
            arguments["query"] = query
        
        logger.info(f"Listing emails (query: {query})")
        return await self.call_tool("list_messages", arguments)
    
    async def close(self):
        """クライアントをクローズ"""
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None
            logger.info("Gmail MCP client closed")

