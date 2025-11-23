"""Github MCP Service - GitHub操作のヘルパー関数群"""

from typing import Dict, Any, List, Optional
import logging

from src.mcp.github.client import GithubMCPClient
from .base import BaseMCPService

logger = logging.getLogger(__name__)


class GithubService(BaseMCPService):
    """GitHub MCP サービス"""
    
    def __init__(self):
        super().__init__("github")
    
    async def initialize(self):
        """GitHubクライアントの初期化"""
        if self._client is None:
            self._client = GithubMCPClient()
            await self._client.__aenter__()
            logger.info("GitHub MCP client initialized")
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        GitHubツールを呼び出し
        
        Args:
            tool_name: ツール名
            arguments: ツールの引数
        
        Returns:
            ツールの実行結果
        """
        await self._ensure_initialized()
        result = await self._client.call_tool(tool_name, arguments)
        return result
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """利用可能なGitHubツールのリストを取得"""
        await self._ensure_initialized()
        tools = await self._client.list_tools()
        return tools.tools if hasattr(tools, 'tools') else []
    
    # ============================================
    # 便利なヘルパーメソッド
    # ============================================
    
    async def create_repository(
        self,
        name: str,
        description: Optional[str] = None,
        private: bool = False
    ) -> Dict[str, Any]:
        """
        GitHubリポジトリを作成
        
        Args:
            name: リポジトリ名
            description: 説明
            private: プライベートリポジトリにするか
        
        Returns:
            作成結果
        """
        arguments = {
            "name": name,
            "private": private
        }
        if description:
            arguments["description"] = description
        
        logger.info(f"Creating GitHub repository: {name}")
        return await self.call_tool("create_repository", arguments)
    
    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        GitHubイシューを作成
        
        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            title: イシューのタイトル
            body: イシューの本文
            labels: ラベルのリスト
        
        Returns:
            作成結果
        """
        arguments = {
            "owner": owner,
            "repo": repo,
            "title": title
        }
        if body:
            arguments["body"] = body
        if labels:
            arguments["labels"] = labels
        
        logger.info(f"Creating GitHub issue: {owner}/{repo} - {title}")
        return await self.call_tool("create_issue", arguments)
    
    async def get_repository(
        self,
        owner: str,
        repo: str
    ) -> Dict[str, Any]:
        """
        リポジトリ情報を取得
        
        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
        
        Returns:
            リポジトリ情報
        """
        logger.info(f"Fetching repository: {owner}/{repo}")
        return await self.call_tool("get_repository", {
            "owner": owner,
            "repo": repo
        })
    
    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open"
    ) -> List[Dict[str, Any]]:
        """
        リポジトリのイシューリストを取得
        
        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            state: イシューの状態（open, closed, all）
        
        Returns:
            イシューのリスト
        """
        logger.info(f"Listing issues for {owner}/{repo} (state: {state})")
        return await self.call_tool("list_issues", {
            "owner": owner,
            "repo": repo,
            "state": state
        })
    
    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        プルリクエストを作成
        
        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            title: PRのタイトル
            head: ヘッドブランチ
            base: ベースブランチ
            body: PRの本文
        
        Returns:
            作成結果
        """
        arguments = {
            "owner": owner,
            "repo": repo,
            "title": title,
            "head": head,
            "base": base
        }
        if body:
            arguments["body"] = body
        
        logger.info(f"Creating pull request: {owner}/{repo} - {title}")
        return await self.call_tool("create_pull_request", arguments)
    
    async def close(self):
        """クライアントをクローズ"""
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None
            logger.info("GitHub MCP client closed")


# グローバルインスタンス
_github_service_instance: Optional[GithubService] = None


async def get_github_service() -> GithubService:
    """GitHubサービスのシングルトンインスタンスを取得"""
    global _github_service_instance
    if _github_service_instance is None:
        _github_service_instance = GithubService()
        await _github_service_instance.initialize()
    return _github_service_instance

