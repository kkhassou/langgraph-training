"""構造化ロギング設定

このモジュールは、JSON形式の構造化ロギングを提供します。
ログにはコンテキスト情報、タイムスタンプ、トレースIDなどが含まれます。

Example:
    >>> from src.core.logging_config import get_logger, setup_logging
    >>> 
    >>> # ロギング設定
    >>> setup_logging()
    >>> 
    >>> # ロガーを取得
    >>> logger = get_logger(__name__)
    >>> 
    >>> # 構造化ログ
    >>> logger.info("User login", extra={
    ...     "user_id": "123",
    ...     "ip_address": "192.168.1.1",
    ...     "action": "login"
    ... })
"""

import logging
import sys
import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import uuid
from contextvars import ContextVar

from pythonjsonlogger import jsonlogger

from src.core.config import settings

# コンテキスト変数（リクエストIDなどの追跡用）
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
workflow_id_var: ContextVar[Optional[str]] = ContextVar('workflow_id', default=None)
node_id_var: ContextVar[Optional[str]] = ContextVar('node_id', default=None)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """カスタムJSONフォーマッター
    
    ログにカスタムフィールドを追加します：
    - timestamp: ISO 8601形式のタイムスタンプ
    - level: ログレベル
    - logger: ロガー名
    - message: ログメッセージ
    - request_id: リクエストID（コンテキストから取得）
    - user_id: ユーザーID（コンテキストから取得）
    - extra: その他のカスタムフィールド
    """
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """ログレコードにカスタムフィールドを追加"""
        super().add_fields(log_record, record, message_dict)
        
        # タイムスタンプ（ISO 8601形式）
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # ログレベル
        log_record['level'] = record.levelname
        
        # ロガー名
        log_record['logger'] = record.name
        
        # ファイル情報
        log_record['file'] = record.pathname
        log_record['line'] = record.lineno
        log_record['function'] = record.funcName
        
        # リクエストID（コンテキストから取得）
        request_id = request_id_var.get()
        if request_id:
            log_record['request_id'] = request_id
        
        # ユーザーID（コンテキストから取得）
        user_id = user_id_var.get()
        if user_id:
            log_record['user_id'] = user_id
        
        # ワークフローID（コンテキストから取得）
        workflow_id = workflow_id_var.get()
        if workflow_id:
            log_record['workflow_id'] = workflow_id
        
        # ノードID（コンテキストから取得）
        node_id = node_id_var.get()
        if node_id:
            log_record['node_id'] = node_id
        
        # 環境情報
        log_record['environment'] = settings.environment
        log_record['app_name'] = settings.app_name


class ContextFilter(logging.Filter):
    """コンテキスト情報をログに追加するフィルター"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """ログレコードにコンテキスト情報を追加"""
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        record.workflow_id = workflow_id_var.get()
        record.node_id = node_id_var.get()
        return True


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    json_format: bool = True
) -> None:
    """ロギング設定を初期化
    
    Args:
        log_level: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
                  省略時はsettings.log_levelを使用
        log_file: ログファイルのパス（省略時はコンソール出力のみ）
        json_format: JSON形式でログを出力するか（デフォルト: True）
    
    Example:
        >>> # コンソールにJSON形式で出力
        >>> setup_logging()
        >>> 
        >>> # ファイルとコンソールに出力
        >>> setup_logging(log_file="logs/app.log")
        >>> 
        >>> # 通常のテキスト形式で出力
        >>> setup_logging(json_format=False)
    """
    # ログレベルの設定
    if log_level is None:
        log_level = settings.log_level
    
    level = getattr(logging, log_level.upper())
    
    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 既存のハンドラーをクリア
    root_logger.handlers.clear()
    
    # フォーマッターの作成
    if json_format:
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(logger)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(ContextFilter())
    root_logger.addHandler(console_handler)
    
    # ファイルハンドラー（オプション）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(ContextFilter())
        root_logger.addHandler(file_handler)
    
    # サードパーティライブラリのログレベルを調整
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    
    root_logger.info(
        "Logging configured",
        extra={
            "log_level": log_level,
            "log_file": log_file,
            "json_format": json_format
        }
    )


def get_logger(name: str) -> logging.Logger:
    """構造化ロガーを取得
    
    Args:
        name: ロガー名（通常は__name__を指定）
    
    Returns:
        logging.Logger: 設定済みのロガー
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing started", extra={"count": 10})
    """
    return logging.getLogger(name)


def set_request_id(request_id: Optional[str] = None) -> str:
    """リクエストIDを設定
    
    Args:
        request_id: リクエストID（省略時は自動生成）
    
    Returns:
        設定されたリクエストID
    
    Example:
        >>> request_id = set_request_id()
        >>> logger.info("Request received")  # request_idが自動的に含まれる
    """
    if request_id is None:
        request_id = str(uuid.uuid4())
    
    request_id_var.set(request_id)
    return request_id


def clear_request_id() -> None:
    """リクエストIDをクリア"""
    request_id_var.set(None)


def set_user_id(user_id: str) -> None:
    """ユーザーIDを設定
    
    Args:
        user_id: ユーザーID
    
    Example:
        >>> set_user_id("user123")
        >>> logger.info("User action")  # user_idが自動的に含まれる
    """
    user_id_var.set(user_id)


def clear_user_id() -> None:
    """ユーザーIDをクリア"""
    user_id_var.set(None)


def set_workflow_id(workflow_id: Optional[str] = None) -> str:
    """ワークフローIDを設定
    
    Args:
        workflow_id: ワークフローID（省略時は自動生成）
    
    Returns:
        設定されたワークフローID
    
    Example:
        >>> workflow_id = set_workflow_id()
        >>> logger.info("Workflow started")  # workflow_idが自動的に含まれる
    """
    if workflow_id is None:
        workflow_id = str(uuid.uuid4())
    
    workflow_id_var.set(workflow_id)
    return workflow_id


def clear_workflow_id() -> None:
    """ワークフローIDをクリア"""
    workflow_id_var.set(None)


def set_node_id(node_id: str) -> None:
    """ノードIDを設定
    
    Args:
        node_id: ノードID
    
    Example:
        >>> set_node_id("llm_node")
        >>> logger.info("Node executing")  # node_idが自動的に含まれる
    """
    node_id_var.set(node_id)


def clear_node_id() -> None:
    """ノードIDをクリア"""
    node_id_var.set(None)


class LogContext:
    """ログコンテキストマネージャー
    
    withステートメント内でリクエストID/ユーザーIDを自動設定・クリア
    
    Example:
        >>> with LogContext(request_id="req-123", user_id="user-456"):
        ...     logger.info("Processing request")
        ...     # request_id と user_id が自動的に含まれる
    """
    
    def __init__(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Args:
            request_id: リクエストID（省略時は自動生成）
            user_id: ユーザーID
        """
        self.request_id = request_id
        self.user_id = user_id
        self._prev_request_id = None
        self._prev_user_id = None
    
    def __enter__(self):
        """コンテキスト開始"""
        # 既存の値を保存
        self._prev_request_id = request_id_var.get()
        self._prev_user_id = user_id_var.get()
        
        # 新しい値を設定
        if self.request_id:
            set_request_id(self.request_id)
        else:
            set_request_id()  # 自動生成
        
        if self.user_id:
            set_user_id(self.user_id)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキスト終了"""
        # 元の値に戻す
        request_id_var.set(self._prev_request_id)
        user_id_var.set(self._prev_user_id)


def log_function_call(logger: logging.Logger):
    """関数呼び出しをログに記録するデコレーター
    
    Args:
        logger: ロガーインスタンス
    
    Example:
        >>> logger = get_logger(__name__)
        >>> 
        >>> @log_function_call(logger)
        ... async def process_data(data):
        ...     return data
        >>> 
        >>> # 関数呼び出しが自動的にログに記録される
        >>> result = await process_data({"key": "value"})
    """
    import functools
    import inspect
    
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.info(
                f"Function call started: {func_name}",
                extra={
                    "function": func_name,
                    "args_count": len(args),
                    "kwargs_count": len(kwargs)
                }
            )
            
            try:
                result = await func(*args, **kwargs)
                logger.info(
                    f"Function call completed: {func_name}",
                    extra={"function": func_name}
                )
                return result
            except Exception as e:
                logger.error(
                    f"Function call failed: {func_name}",
                    extra={
                        "function": func_name,
                        "error": str(e),
                        "error_type": type(e).__name__
                    },
                    exc_info=True
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.info(
                f"Function call started: {func_name}",
                extra={
                    "function": func_name,
                    "args_count": len(args),
                    "kwargs_count": len(kwargs)
                }
            )
            
            try:
                result = func(*args, **kwargs)
                logger.info(
                    f"Function call completed: {func_name}",
                    extra={"function": func_name}
                )
                return result
            except Exception as e:
                logger.error(
                    f"Function call failed: {func_name}",
                    extra={
                        "function": func_name,
                        "error": str(e),
                        "error_type": type(e).__name__
                    },
                    exc_info=True
                )
                raise
        
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class StructuredLogger:
    """構造化ロギングの高レベルラッパー
    
    ワークフロー、ノード、プロバイダーのロギングを簡単にするためのクラス。
    自動的にコンテキスト情報を含め、イベントタイプごとに適切なログを記録します。
    
    Example:
        >>> logger = StructuredLogger(__name__)
        >>> 
        >>> # ワークフロー開始
        >>> logger.workflow_start("chat_workflow", {"message": "Hello"})
        >>> 
        >>> # ノード実行
        >>> logger.node_execute("llm_node", "LLMNode", 0.523)
        >>> 
        >>> # ワークフロー完了
        >>> logger.workflow_end("chat_workflow", 1.234, success=True)
    """
    
    def __init__(self, name: str):
        """
        Args:
            name: ロガー名（通常は__name__）
        """
        self.logger = get_logger(name)
    
    def _add_context(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """コンテキスト情報を追加"""
        context = {
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            **data
        }
        
        # コンテキスト変数から取得
        request_id = request_id_var.get()
        if request_id:
            context["request_id"] = request_id
        
        user_id = user_id_var.get()
        if user_id:
            context["user_id"] = user_id
        
        workflow_id = workflow_id_var.get()
        if workflow_id:
            context["workflow_id"] = workflow_id
        
        node_id = node_id_var.get()
        if node_id:
            context["node_id"] = node_id
        
        return context
    
    def info(self, message: str, **kwargs):
        """INFOレベルログ"""
        self.logger.info(message, extra=self._add_context(kwargs))
    
    def warning(self, message: str, **kwargs):
        """WARNINGレベルログ"""
        self.logger.warning(message, extra=self._add_context(kwargs))
    
    def error(self, message: str, exc_info=None, **kwargs):
        """ERRORレベルログ"""
        self.logger.error(message, extra=self._add_context(kwargs), exc_info=exc_info)
    
    def debug(self, message: str, **kwargs):
        """DEBUGレベルログ"""
        self.logger.debug(message, extra=self._add_context(kwargs))
    
    def workflow_start(self, workflow_name: str, input_data: Dict[str, Any]):
        """ワークフロー開始ログ
        
        Args:
            workflow_name: ワークフロー名
            input_data: 入力データ（キーのみ記録）
        
        Example:
            >>> logger.workflow_start("chat_workflow", {"message": "Hello"})
        """
        self.info(
            f"Workflow started: {workflow_name}",
            event_type="workflow_start",
            workflow_name=workflow_name,
            input_keys=list(input_data.keys()) if isinstance(input_data, dict) else []
        )
    
    def workflow_end(self, workflow_name: str, duration: float, success: bool, error: Optional[str] = None):
        """ワークフロー完了ログ
        
        Args:
            workflow_name: ワークフロー名
            duration: 実行時間（秒）
            success: 成功したかどうか
            error: エラーメッセージ（失敗時）
        
        Example:
            >>> logger.workflow_end("chat_workflow", 1.234, success=True)
        """
        if success:
            self.info(
                f"Workflow completed: {workflow_name}",
                event_type="workflow_end",
                workflow_name=workflow_name,
                duration_seconds=duration,
                duration_ms=duration * 1000,
                success=success
            )
        else:
            self.error(
                f"Workflow failed: {workflow_name}",
                event_type="workflow_end",
                workflow_name=workflow_name,
                duration_seconds=duration,
                duration_ms=duration * 1000,
                success=success,
                error=error
            )
    
    def node_execute(self, node_name: str, node_type: str, duration: float, success: bool = True):
        """ノード実行ログ
        
        Args:
            node_name: ノード名
            node_type: ノードタイプ
            duration: 実行時間（秒）
            success: 成功したかどうか
        
        Example:
            >>> logger.node_execute("llm_node", "LLMNode", 0.523)
        """
        self.info(
            f"Node executed: {node_name}",
            event_type="node_execute",
            node_name=node_name,
            node_type=node_type,
            duration_seconds=duration,
            duration_ms=duration * 1000,
            success=success
        )
    
    def provider_call(self, provider_name: str, method: str, duration: float, success: bool = True):
        """プロバイダー呼び出しログ
        
        Args:
            provider_name: プロバイダー名
            method: メソッド名
            duration: 実行時間（秒）
            success: 成功したかどうか
        
        Example:
            >>> logger.provider_call("GeminiProvider", "generate", 0.823)
        """
        self.info(
            f"Provider call: {provider_name}.{method}",
            event_type="provider_call",
            provider_name=provider_name,
            method=method,
            duration_seconds=duration,
            duration_ms=duration * 1000,
            success=success
        )
    
    def api_request(self, method: str, path: str, status_code: int, duration: float):
        """APIリクエストログ
        
        Args:
            method: HTTPメソッド
            path: パス
            status_code: ステータスコード
            duration: 実行時間（秒）
        
        Example:
            >>> logger.api_request("POST", "/workflows/chat", 200, 1.234)
        """
        self.info(
            f"API request: {method} {path}",
            event_type="api_request",
            http_method=method,
            path=path,
            status_code=status_code,
            duration_seconds=duration,
            duration_ms=duration * 1000
        )


def get_structured_logger(name: str) -> StructuredLogger:
    """構造化ロガーを取得
    
    Args:
        name: ロガー名（通常は__name__）
    
    Returns:
        StructuredLogger: 構造化ロガーインスタンス
    
    Example:
        >>> logger = get_structured_logger(__name__)
        >>> logger.workflow_start("my_workflow", {"input": "data"})
    """
    return StructuredLogger(name)


if __name__ == "__main__":
    # テスト実行
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("This is an info message")
    logger.warning("This is a warning", extra={"key": "value"})
    
    with LogContext(user_id="test-user"):
        logger.info("Message with context")
    
    logger.info("Message after context")
    
    # 構造化ロガーのテスト
    structured_logger = get_structured_logger(__name__)
    structured_logger.workflow_start("test_workflow", {"message": "test"})
    structured_logger.node_execute("test_node", "TestNode", 0.5)
    structured_logger.workflow_end("test_workflow", 1.0, success=True)

