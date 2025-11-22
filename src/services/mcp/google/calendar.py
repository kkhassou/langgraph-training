"""Google Calendar MCP Service - Calendar操作のヘルパー関数群"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from src.mcp.google.calendar.client import CalendarMCPClient
from ..base import BaseMCPService

logger = logging.getLogger(__name__)


class CalendarService(BaseMCPService):
    """Google Calendar MCP サービス"""
    
    def __init__(self):
        super().__init__("calendar")
    
    async def initialize(self):
        """Calendarクライアントの初期化"""
        if self._client is None:
            self._client = CalendarMCPClient()
            await self._client.__aenter__()
            logger.info("Calendar MCP client initialized")
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calendarツールを呼び出し"""
        await self._ensure_initialized()
        result = await self._client.call_tool(tool_name, arguments)
        return result
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """利用可能なCalendarツールのリストを取得"""
        await self._ensure_initialized()
        tools = await self._client.list_tools()
        return tools.tools if hasattr(tools, 'tools') else []
    
    # ============================================
    # 便利なヘルパーメソッド
    # ============================================
    
    async def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        カレンダーイベントを作成
        
        Args:
            summary: イベントのタイトル
            start_time: 開始時刻
            end_time: 終了時刻
            description: 説明
            location: 場所
            attendees: 参加者のメールアドレスリスト
        
        Returns:
            作成結果
        """
        arguments = {
            "summary": summary,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        if description:
            arguments["description"] = description
        if location:
            arguments["location"] = location
        if attendees:
            arguments["attendees"] = attendees
        
        logger.info(f"Creating calendar event: {summary}")
        return await self.call_tool("create_event", arguments)
    
    async def list_events(
        self,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        カレンダーイベントのリストを取得
        
        Args:
            time_min: 開始時刻の下限
            time_max: 開始時刻の上限
            max_results: 最大取得件数
        
        Returns:
            イベントのリスト
        """
        arguments = {"max_results": max_results}
        if time_min:
            arguments["time_min"] = time_min.isoformat()
        if time_max:
            arguments["time_max"] = time_max.isoformat()
        
        logger.info("Listing calendar events")
        return await self.call_tool("list_events", arguments)
    
    async def close(self):
        """クライアントをクローズ"""
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None
            logger.info("Calendar MCP client closed")

