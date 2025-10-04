"""カスタム例外定義"""


class LangGraphBaseException(Exception):
    """基底例外クラス"""
    pass


class NodeExecutionError(LangGraphBaseException):
    """ノード実行エラー"""
    pass


class MCPError(LangGraphBaseException):
    """MCP関連エラー"""
    pass


class VectorStoreError(LangGraphBaseException):
    """ベクトルストアエラー"""
    pass


class EmbeddingError(LangGraphBaseException):
    """埋め込み生成エラー"""
    pass


class ConfigurationError(LangGraphBaseException):
    """設定エラー"""
    pass
