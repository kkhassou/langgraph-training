"""Notion Integration Node

Notionとの統合を行うノード実装。
MCP (Model Context Protocol) サーバーを介してNotion APIと通信します。
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import logging

from src.mcp.notion.client import NotionMCPService
from src.nodes.base import BaseNode, NodeResult

logger = logging.getLogger(__name__)


class NotionInput(BaseModel):
    """Notionノードの入力スキーマ"""
    
    action: str = Field(
        ...,
        description="Action to perform: create_page, get_page, update_page, query_database, create_database_entry, search"
    )

    # Common parameters
    page_id: Optional[str] = Field(None, description="Page ID")
    parent_id: Optional[str] = Field(None, description="Parent page or database ID")
    database_id: Optional[str] = Field(None, description="Database ID")

    # For create_page and update_page
    title: Optional[str] = Field(None, description="Page title")
    content: Optional[str] = Field(None, description="Page content")

    # For query_database
    filter: Optional[Dict[str, Any]] = Field(None, description="Filter conditions")
    sorts: Optional[List[Dict[str, Any]]] = Field(None, description="Sort options")
    page_size: Optional[int] = Field(10, description="Number of results")

    # For create_database_entry
    properties: Optional[Dict[str, Any]] = Field(None, description="Entry properties")

    # For search
    query: Optional[str] = Field(None, description="Search query")


class NotionNode(BaseNode):
    """Notion統合ノード
    
    MCPサーバーを介してNotion APIと通信し、以下の機能を提供します：
    - ページの作成・取得・更新
    - データベースのクエリ
    - データベースエントリの作成
    - 検索
    
    Attributes:
        notion_service: NotionMCPServiceインスタンス
    
    Example:
        >>> node = NotionNode()
        >>> input_data = {
        ...     "action": "create_page",
        ...     "parent_id": "page-id",
        ...     "title": "New Page",
        ...     "content": "Page content"
        ... }
        >>> result = await node.execute(input_data)
    """

    def __init__(self):
        super().__init__("notion_node")
        self.notion_service = NotionMCPService()

    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """Notion操作を実行
        
        Args:
            input_data: 入力データ
                - action: 実行するアクション
                - その他アクション固有のパラメータ
        
        Returns:
            NodeResult: 実行結果
                - success: 成功/失敗フラグ
                - data: 取得/作成したデータ
                - error: エラーメッセージ（エラー時）
                - metadata: メタデータ
        """
        try:
            action = input_data.get("action")

            if action == "create_page":
                parent_id = input_data.get("parent_id")
                title = input_data.get("title", "Untitled")
                content = input_data.get("content")

                if not parent_id:
                    raise ValueError("parent_id is required for create_page action")

                result = await self.notion_service.create_page(parent_id, title, content)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "create_page", "title": title}
                )

            elif action == "get_page":
                page_id = input_data.get("page_id")
                if not page_id:
                    raise ValueError("page_id is required for get_page action")

                result = await self.notion_service.get_page(page_id)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "get_page", "page_id": page_id}
                )

            elif action == "update_page":
                page_id = input_data.get("page_id")
                title = input_data.get("title")

                if not page_id:
                    raise ValueError("page_id is required for update_page action")

                result = await self.notion_service.update_page(page_id, title)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "update_page", "page_id": page_id}
                )

            elif action == "query_database":
                database_id = input_data.get("database_id")
                filter_obj = input_data.get("filter")
                sorts = input_data.get("sorts")
                page_size = input_data.get("page_size", 10)

                if not database_id:
                    raise ValueError("database_id is required for query_database action")

                result = await self.notion_service.query_database(
                    database_id, filter_obj, sorts, page_size
                )
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "query_database", "database_id": database_id}
                )

            elif action == "create_database_entry":
                database_id = input_data.get("database_id")
                properties = input_data.get("properties")

                if not database_id:
                    raise ValueError("database_id is required for create_database_entry action")
                if not properties:
                    raise ValueError("properties is required for create_database_entry action")

                result = await self.notion_service.create_database_entry(database_id, properties)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "create_database_entry", "database_id": database_id}
                )

            elif action == "search":
                query = input_data.get("query")
                filter_obj = input_data.get("filter")

                if not query:
                    raise ValueError("query is required for search action")

                result = await self.notion_service.search(query, filter_obj)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "search", "query": query}
                )

            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Error in Notion node: {e}")
            return NodeResult(
                success=False,
                error=str(e),
                metadata={"action": input_data.get("action")}
            )

    async def cleanup(self):
        """Notionサービス接続のクリーンアップ"""
        try:
            await self.notion_service.disconnect()
        except Exception as e:
            logger.error(f"Error during Notion cleanup: {e}")


# Create node instance
notion_node = NotionNode()


async def notion_node_handler(input_data: NotionInput) -> Dict[str, Any]:
    """Notionノードのスタンドアロンハンドラー
    
    APIエンドポイントから直接呼び出される場合に使用します。
    
    Args:
        input_data: Notion操作の入力パラメータ
    
    Returns:
        Dict[str, Any]: 実行結果
    """
    result = await notion_node.execute(input_data.model_dump())
    return result.model_dump()

