"""Prometheusメトリクス収集

このモジュールは、Prometheusメトリクスの収集と公開を提供します。
LLM呼び出し、ワークフロー実行、エラー率などを監視できます。

Example:
    >>> from src.core.metrics import metrics
    >>> 
    >>> # LLM呼び出しをカウント
    >>> metrics.llm_requests_total.labels(
    ...     provider="gemini",
    ...     model="gemini-2.0-flash-exp"
    ... ).inc()
    >>> 
    >>> # レスポンス時間を記録
    >>> with metrics.llm_request_duration.labels(provider="gemini").time():
    ...     response = await provider.generate("Hello")
"""

import time
from typing import Optional, Callable, Any
import functools
import inspect

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST
)

from src.core.config import settings


class MetricsCollector:
    """メトリクスコレクター
    
    アプリケーション全体のメトリクスを収集・管理します。
    
    Attributes:
        registry: Prometheusレジストリ
        
        # アプリケーション情報
        app_info: アプリケーション情報
        
        # LLMメトリクス
        llm_requests_total: LLM呼び出し回数
        llm_request_duration: LLMリクエスト時間
        llm_tokens_total: トークン使用量
        llm_errors_total: LLMエラー回数
        
        # ワークフローメトリクス
        workflow_executions_total: ワークフロー実行回数
        workflow_duration: ワークフロー実行時間
        workflow_errors_total: ワークフローエラー回数
        
        # ノードメトリクス
        node_executions_total: ノード実行回数
        node_duration: ノード実行時間
        node_errors_total: ノードエラー回数
        
        # システムメトリクス
        active_requests: アクティブなリクエスト数
        http_requests_total: HTTPリクエスト回数
        http_request_duration: HTTPリクエスト時間
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Args:
            registry: Prometheusレジストリ（省略時は新規作成）
        """
        self.registry = registry or CollectorRegistry()
        
        # ============================================================================
        # アプリケーション情報
        # ============================================================================
        
        self.app_info = Info(
            'langgraph_app',
            'Application information',
            registry=self.registry
        )
        self.app_info.info({
            'app_name': settings.app_name,
            'environment': settings.environment,
            'version': '1.0.0'  # TODO: バージョン管理システムから取得
        })
        
        # ============================================================================
        # LLMメトリクス
        # ============================================================================
        
        self.llm_requests_total = Counter(
            'langgraph_llm_requests_total',
            'Total number of LLM requests',
            ['provider', 'model', 'method'],
            registry=self.registry
        )
        
        self.llm_request_duration = Histogram(
            'langgraph_llm_request_duration_seconds',
            'LLM request duration in seconds',
            ['provider', 'model', 'method'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
            registry=self.registry
        )
        
        self.llm_tokens_total = Counter(
            'langgraph_llm_tokens_total',
            'Total number of tokens used',
            ['provider', 'model', 'type'],  # type: input/output
            registry=self.registry
        )
        
        self.llm_errors_total = Counter(
            'langgraph_llm_errors_total',
            'Total number of LLM errors',
            ['provider', 'model', 'error_type'],
            registry=self.registry
        )
        
        # ============================================================================
        # ワークフローメトリクス
        # ============================================================================
        
        self.workflow_executions_total = Counter(
            'langgraph_workflow_executions_total',
            'Total number of workflow executions',
            ['workflow_name', 'status'],  # status: success/failure
            registry=self.registry
        )
        
        self.workflow_duration = Histogram(
            'langgraph_workflow_duration_seconds',
            'Workflow execution duration in seconds',
            ['workflow_name'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
            registry=self.registry
        )
        
        self.workflow_errors_total = Counter(
            'langgraph_workflow_errors_total',
            'Total number of workflow errors',
            ['workflow_name', 'error_type'],
            registry=self.registry
        )
        
        # ============================================================================
        # ノードメトリクス
        # ============================================================================
        
        self.node_executions_total = Counter(
            'langgraph_node_executions_total',
            'Total number of node executions',
            ['node_name', 'node_type', 'status'],
            registry=self.registry
        )
        
        self.node_duration = Histogram(
            'langgraph_node_duration_seconds',
            'Node execution duration in seconds',
            ['node_name', 'node_type'],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
            registry=self.registry
        )
        
        self.node_errors_total = Counter(
            'langgraph_node_errors_total',
            'Total number of node errors',
            ['node_name', 'node_type', 'error_type'],
            registry=self.registry
        )
        
        # ============================================================================
        # RAGメトリクス
        # ============================================================================
        
        self.rag_queries_total = Counter(
            'langgraph_rag_queries_total',
            'Total number of RAG queries',
            ['provider', 'status'],
            registry=self.registry
        )
        
        self.rag_query_duration = Histogram(
            'langgraph_rag_query_duration_seconds',
            'RAG query duration in seconds',
            ['provider'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
            registry=self.registry
        )
        
        self.rag_documents_retrieved = Histogram(
            'langgraph_rag_documents_retrieved',
            'Number of documents retrieved by RAG',
            ['provider'],
            buckets=(1, 3, 5, 10, 20, 50),
            registry=self.registry
        )
        
        # ============================================================================
        # システムメトリクス
        # ============================================================================
        
        self.active_requests = Gauge(
            'langgraph_active_requests',
            'Number of active requests',
            registry=self.registry
        )
        
        self.http_requests_total = Counter(
            'langgraph_http_requests_total',
            'Total number of HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.http_request_duration = Histogram(
            'langgraph_http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0),
            registry=self.registry
        )
        
        # ============================================================================
        # プラグインメトリクス
        # ============================================================================
        
        self.plugins_loaded_total = Gauge(
            'langgraph_plugins_loaded_total',
            'Number of loaded plugins',
            registry=self.registry
        )
        
        self.plugin_load_errors_total = Counter(
            'langgraph_plugin_load_errors_total',
            'Total number of plugin load errors',
            ['plugin_name'],
            registry=self.registry
        )
    
    def get_metrics(self) -> bytes:
        """Prometheus形式のメトリクスを取得
        
        Returns:
            Prometheus形式のメトリクステキスト
        
        Example:
            >>> metrics_text = metrics.get_metrics()
            >>> print(metrics_text.decode('utf-8'))
        """
        return generate_latest(self.registry)
    
    def track_llm_request(self, provider: str, model: str, method: str):
        """LLMリクエストを追跡するコンテキストマネージャー
        
        Args:
            provider: プロバイダー名
            model: モデル名
            method: メソッド名（generate, generate_json, etc）
        
        Example:
            >>> with metrics.track_llm_request("gemini", "gemini-2.0-flash-exp", "generate"):
            ...     response = await provider.generate("Hello")
        """
        return _MetricTracker(
            self,
            'llm',
            labels={'provider': provider, 'model': model, 'method': method}
        )
    
    def track_workflow(self, workflow_name: str):
        """ワークフロー実行を追跡するコンテキストマネージャー
        
        Args:
            workflow_name: ワークフロー名
        
        Example:
            >>> with metrics.track_workflow("chat_workflow"):
            ...     result = await workflow.run(input_data)
        """
        return _MetricTracker(
            self,
            'workflow',
            labels={'workflow_name': workflow_name}
        )
    
    def track_node(self, node_name: str, node_type: str):
        """ノード実行を追跡するコンテキストマネージャー
        
        Args:
            node_name: ノード名
            node_type: ノードタイプ
        
        Example:
            >>> with metrics.track_node("llm_node", "llm"):
            ...     result = await node.execute(state)
        """
        return _MetricTracker(
            self,
            'node',
            labels={'node_name': node_name, 'node_type': node_type}
        )


class _MetricTracker:
    """メトリクス追跡コンテキストマネージャー"""
    
    def __init__(self, collector: MetricsCollector, metric_type: str, labels: dict):
        self.collector = collector
        self.metric_type = metric_type
        self.labels = labels
        self.start_time = None
        self.error = None
    
    def __enter__(self):
        self.start_time = time.time()
        
        # アクティブリクエストをカウント（システムメトリクス）
        if self.metric_type == 'llm':
            self.collector.active_requests.inc()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if self.metric_type == 'llm':
            # LLMメトリクス
            self.collector.llm_requests_total.labels(**self.labels).inc()
            self.collector.llm_request_duration.labels(**self.labels).observe(duration)
            self.collector.active_requests.dec()
            
            if exc_type:
                self.collector.llm_errors_total.labels(
                    **self.labels,
                    error_type=exc_type.__name__
                ).inc()
        
        elif self.metric_type == 'workflow':
            # ワークフローメトリクス
            status = 'failure' if exc_type else 'success'
            self.collector.workflow_executions_total.labels(
                **self.labels,
                status=status
            ).inc()
            self.collector.workflow_duration.labels(**self.labels).observe(duration)
            
            if exc_type:
                self.collector.workflow_errors_total.labels(
                    **self.labels,
                    error_type=exc_type.__name__
                ).inc()
        
        elif self.metric_type == 'node':
            # ノードメトリクス
            status = 'failure' if exc_type else 'success'
            self.collector.node_executions_total.labels(
                **self.labels,
                status=status
            ).inc()
            self.collector.node_duration.labels(**self.labels).observe(duration)
            
            if exc_type:
                self.collector.node_errors_total.labels(
                    **self.labels,
                    error_type=exc_type.__name__
                ).inc()
        
        # 例外を再発生させない（メトリクス収集は透過的）
        return False


def track_metrics(metric_type: str, **labels):
    """メトリクスを追跡するデコレーター
    
    Args:
        metric_type: メトリクスタイプ（llm, workflow, node）
        **labels: ラベル
    
    Example:
        >>> @track_metrics('llm', provider='gemini', model='gemini-2.0-flash-exp', method='generate')
        ... async def generate_text(prompt):
        ...     return await provider.generate(prompt)
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with metrics.track_llm_request(**labels) if metric_type == 'llm' else \
                 metrics.track_workflow(**labels) if metric_type == 'workflow' else \
                 metrics.track_node(**labels):
                return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with metrics.track_llm_request(**labels) if metric_type == 'llm' else \
                 metrics.track_workflow(**labels) if metric_type == 'workflow' else \
                 metrics.track_node(**labels):
                return func(*args, **kwargs)
        
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# グローバルメトリクスインスタンス
metrics = MetricsCollector()


def get_metrics_text() -> str:
    """Prometheus形式のメトリクステキストを取得
    
    Returns:
        メトリクステキスト
    
    Example:
        >>> print(get_metrics_text())
    """
    return metrics.get_metrics().decode('utf-8')


if __name__ == "__main__":
    # テスト実行
    import asyncio
    
    async def test():
        # LLMリクエストをシミュレート
        with metrics.track_llm_request("gemini", "gemini-2.0-flash-exp", "generate"):
            await asyncio.sleep(0.5)
        
        # ワークフロー実行をシミュレート
        with metrics.track_workflow("chat_workflow"):
            await asyncio.sleep(1.0)
        
        # メトリクスを表示
        print(get_metrics_text())
    
    asyncio.run(test())

