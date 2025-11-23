"""Base MCP Service - MCP サービスの基底クラス"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class BaseMCPService(ABC):
    """MCPサービスの基底クラス"""
    
    def __init__(self, service_name: str):
        """
        Args:
            service_name: サービス名（slack, github, gmail など）
        """
        self.service_name = service_name
        self._client = None
    
    @abstractmethod
    async def initialize(self):
        """
        サービスの初期化
        
        サブクラスでクライアントの初期化を実装
        """
        pass
    
    async def _ensure_initialized(self):
        """クライアントが初期化されているか確認"""
        if self._client is None:
            await self.initialize()
    
    @abstractmethod
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        MCPツールを呼び出し
        
        Args:
            tool_name: ツール名
            arguments: ツールの引数
        
        Returns:
            ツールの実行結果
        """
        pass
    
    @abstractmethod
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        利用可能なツールのリストを取得
        
        Returns:
            ツールのリスト
        """
        pass
    
    async def health_check(self) -> bool:
        """
        サービスの健全性チェック
        
        Returns:
            サービスが正常かどうか
        """
        try:
            await self._ensure_initialized()
            return self._client is not None
        except Exception as e:
            logger.error(f"{self.service_name} health check failed: {e}")
            return False
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(service={self.service_name})"

