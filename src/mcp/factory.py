"""MCP Client Factory

MCPクライアントを生成するFactoryパターン実装
"""
from typing import Dict, Any, Type
from .base import BaseMCPClient
from .slack.client import SlackMCPClient
from .github.client import GitHubMCPClient
from .notion.client import NotionMCPClient
from .google.gmail.client import GmailMCPClient
from .google.calendar.client import CalendarMCPClient
from .google.sheets.client import SheetsMCPClient
from .google.docs.client import DocsMCPClient
from .google.slides.client import SlidesMCPClient
from .google.forms.client import FormsMCPClient
from .google.keep.client import KeepMCPClient
from .google.apps_script.client import AppsScriptMCPClient
from .google.vertex_ai.client import VertexAIMCPClient


class MCPClientFactory:
    """MCPクライアント生成Factory"""

    _clients: Dict[str, Type[BaseMCPClient]] = {
        "slack": SlackMCPClient,
        "github": GitHubMCPClient,
        "notion": NotionMCPClient,
        "gmail": GmailMCPClient,
        "google_calendar": CalendarMCPClient,
        "google_sheets": SheetsMCPClient,
        "google_docs": DocsMCPClient,
        "google_slides": SlidesMCPClient,
        "google_forms": FormsMCPClient,
        "google_keep": KeepMCPClient,
        "google_apps_script": AppsScriptMCPClient,
        "vertex_ai": VertexAIMCPClient,
    }

    @classmethod
    def create_client(cls, service_type: str, **kwargs) -> BaseMCPClient:
        """MCPクライアント生成

        Args:
            service_type: サービスタイプ（slack, notion, gmail等）
            **kwargs: クライアント固有の設定

        Returns:
            BaseMCPClient: MCPクライアントインスタンス

        Raises:
            ValueError: 未知のサービスタイプの場合
        """
        client_class = cls._clients.get(service_type)
        if not client_class:
            raise ValueError(f"Unknown MCP service type: {service_type}")

        return client_class(**kwargs)

    @classmethod
    def register_client(cls, service_type: str, client_class: Type[BaseMCPClient]):
        """新規MCPクライアントを登録

        Args:
            service_type: サービスタイプ名
            client_class: MCPクライアントクラス
        """
        cls._clients[service_type] = client_class

    @classmethod
    def list_supported_services(cls) -> list:
        """サポートされているサービス一覧を取得

        Returns:
            list: サポートされているサービスタイプのリスト
        """
        return list(cls._clients.keys())
