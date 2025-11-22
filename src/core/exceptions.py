"""カスタム例外定義

このモジュールは、プロジェクト全体で使用される構造化された例外クラスを提供します。
各例外は、詳細なコンテキスト情報を含むことができます。
"""

from typing import Optional, Dict, Any


class LangGraphBaseException(Exception):
    """基底例外クラス
    
    全てのカスタム例外の基底クラス。
    詳細なエラー情報とコンテキストを保持できます。
    
    Attributes:
        message: エラーメッセージ
        details: エラーの詳細情報
        original_error: 元の例外（あれば）
    """
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        self.message = message
        self.details = details or {}
        self.original_error = original_error
        super().__init__(self.format_message())
    
    def format_message(self) -> str:
        """エラーメッセージをフォーマット"""
        msg = self.message
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            msg = f"{msg} ({detail_str})"
        if self.original_error:
            msg = f"{msg} [原因: {type(self.original_error).__name__}: {str(self.original_error)}]"
        return msg
    
    def to_dict(self) -> Dict[str, Any]:
        """例外情報を辞書形式で返す"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "original_error": str(self.original_error) if self.original_error else None
        }


# ============================================================================
# Provider Layer Exceptions
# ============================================================================

class ProviderError(LangGraphBaseException):
    """プロバイダー関連の基底エラー"""
    pass


class LLMProviderError(ProviderError):
    """LLMプロバイダーエラー"""
    pass


class LLMGenerationError(LLMProviderError):
    """LLM生成エラー"""
    pass


class LLMJSONParseError(LLMProviderError):
    """LLM JSON パースエラー"""
    pass


class LLMRateLimitError(LLMProviderError):
    """LLM レート制限エラー"""
    pass


class LLMAuthenticationError(LLMProviderError):
    """LLM 認証エラー"""
    pass


class RAGProviderError(ProviderError):
    """RAGプロバイダーエラー"""
    pass


# ============================================================================
# Node Layer Exceptions
# ============================================================================

class NodeError(LangGraphBaseException):
    """ノード関連の基底エラー"""
    pass


class NodeExecutionError(NodeError):
    """ノード実行エラー"""
    pass


class NodeInputValidationError(NodeError):
    """ノード入力検証エラー"""
    pass


class NodeOutputValidationError(NodeError):
    """ノード出力検証エラー"""
    pass


# ============================================================================
# Workflow Layer Exceptions
# ============================================================================

class WorkflowError(LangGraphBaseException):
    """ワークフロー関連の基底エラー"""
    pass


class WorkflowExecutionError(WorkflowError):
    """ワークフロー実行エラー"""
    pass


class WorkflowBuildError(WorkflowError):
    """ワークフローグラフ構築エラー"""
    pass


# ============================================================================
# Infrastructure Layer Exceptions
# ============================================================================

class InfrastructureError(LangGraphBaseException):
    """インフラ関連の基底エラー"""
    pass


class VectorStoreError(InfrastructureError):
    """ベクトルストアエラー"""
    pass


class VectorStoreConnectionError(VectorStoreError):
    """ベクトルストア接続エラー"""
    pass


class VectorStoreQueryError(VectorStoreError):
    """ベクトルストアクエリエラー"""
    pass


class EmbeddingError(InfrastructureError):
    """埋め込み生成エラー"""
    pass


class EmbeddingDimensionError(EmbeddingError):
    """埋め込み次元エラー"""
    pass


class SearchError(InfrastructureError):
    """検索エラー"""
    pass


# ============================================================================
# MCP Layer Exceptions
# ============================================================================

class MCPError(LangGraphBaseException):
    """MCP関連の基底エラー"""
    pass


class MCPConnectionError(MCPError):
    """MCP接続エラー"""
    pass


class MCPToolError(MCPError):
    """MCPツール実行エラー"""
    pass


class MCPAuthenticationError(MCPError):
    """MCP認証エラー"""
    pass


# ============================================================================
# Configuration Exceptions
# ============================================================================

class ConfigurationError(LangGraphBaseException):
    """設定エラー"""
    pass


class MissingConfigError(ConfigurationError):
    """必須設定が欠落している"""
    pass


class InvalidConfigError(ConfigurationError):
    """無効な設定値"""
    pass


# ============================================================================
# Factory Exceptions
# ============================================================================

class FactoryError(LangGraphBaseException):
    """ファクトリー関連エラー"""
    pass


class UnknownProviderError(FactoryError):
    """未知のプロバイダータイプ"""
    pass


class ProviderRegistrationError(FactoryError):
    """プロバイダー登録エラー"""
    pass
