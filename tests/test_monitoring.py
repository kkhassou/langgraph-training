"""監視とロギングのテスト"""

import pytest
import logging
import time
from unittest.mock import Mock, patch

# Note: 実際のテストを実行するにはpython-json-loggerとprometheus-clientが必要
# pip install python-json-logger prometheus-client

try:
    from src.core.logging_config import (
        setup_logging,
        get_logger,
        set_request_id,
        clear_request_id,
        set_user_id,
        clear_user_id,
        LogContext
    )
    from src.core.metrics import (
        metrics,
        MetricsCollector,
        get_metrics_text,
        track_metrics
    )
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required packages not installed")
class TestLoggingConfig:
    """ロギング設定のテスト"""
    
    def test_setup_logging(self):
        """ロギング設定のテスト"""
        setup_logging(log_level="INFO", json_format=False)
        
        logger = logging.getLogger()
        assert logger.level == logging.INFO
    
    def test_get_logger(self):
        """ロガー取得のテスト"""
        logger = get_logger(__name__)
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == __name__
    
    def test_set_request_id(self):
        """リクエストID設定のテスト"""
        request_id = set_request_id()
        
        assert request_id is not None
        assert len(request_id) == 36  # UUID形式
        
        clear_request_id()
    
    def test_set_custom_request_id(self):
        """カスタムリクエストID設定のテスト"""
        custom_id = "custom-request-123"
        result = set_request_id(custom_id)
        
        assert result == custom_id
        
        clear_request_id()
    
    def test_set_user_id(self):
        """ユーザーID設定のテスト"""
        user_id = "user-123"
        set_user_id(user_id)
        
        # ユーザーIDがコンテキストに設定されることを確認
        # （実際のテストではログ出力を確認）
        
        clear_user_id()
    
    def test_log_context_manager(self):
        """ログコンテキストマネージャーのテスト"""
        with LogContext(request_id="test-req", user_id="test-user"):
            # コンテキスト内でリクエストIDとユーザーIDが設定される
            pass
        
        # コンテキスト外ではクリアされる


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required packages not installed")
class TestMetricsCollector:
    """メトリクスコレクターのテスト"""
    
    def setup_method(self):
        """各テストの前にメトリクスをリセット"""
        # 新しいコレクターを作成
        from prometheus_client import CollectorRegistry
        self.registry = CollectorRegistry()
        self.collector = MetricsCollector(registry=self.registry)
    
    def test_llm_metrics(self):
        """LLMメトリクスのテスト"""
        self.collector.llm_requests_total.labels(
            provider="gemini",
            model="test-model",
            method="generate"
        ).inc()
        
        # メトリクスが記録されることを確認
        metrics_text = self.collector.get_metrics().decode('utf-8')
        assert "langgraph_llm_requests_total" in metrics_text
        assert "gemini" in metrics_text
    
    def test_workflow_metrics(self):
        """ワークフローメトリクスのテスト"""
        self.collector.workflow_executions_total.labels(
            workflow_name="test_workflow",
            status="success"
        ).inc()
        
        metrics_text = self.collector.get_metrics().decode('utf-8')
        assert "langgraph_workflow_executions_total" in metrics_text
    
    def test_node_metrics(self):
        """ノードメトリクスのテスト"""
        self.collector.node_executions_total.labels(
            node_name="test_node",
            node_type="llm",
            status="success"
        ).inc()
        
        metrics_text = self.collector.get_metrics().decode('utf-8')
        assert "langgraph_node_executions_total" in metrics_text
    
    def test_llm_request_tracking(self):
        """LLMリクエスト追跡のテスト"""
        with self.collector.track_llm_request("gemini", "test-model", "generate"):
            time.sleep(0.01)
        
        # リクエストがカウントされることを確認
        metrics_text = self.collector.get_metrics().decode('utf-8')
        assert "langgraph_llm_requests_total" in metrics_text
        assert "langgraph_llm_request_duration_seconds" in metrics_text
    
    def test_llm_request_tracking_with_error(self):
        """エラー時のLLMリクエスト追跡のテスト"""
        try:
            with self.collector.track_llm_request("gemini", "test-model", "generate"):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # エラーがカウントされることを確認
        metrics_text = self.collector.get_metrics().decode('utf-8')
        assert "langgraph_llm_errors_total" in metrics_text
    
    def test_workflow_tracking(self):
        """ワークフロー追跡のテスト"""
        with self.collector.track_workflow("test_workflow"):
            time.sleep(0.01)
        
        metrics_text = self.collector.get_metrics().decode('utf-8')
        assert "langgraph_workflow_executions_total" in metrics_text
    
    def test_node_tracking(self):
        """ノード追跡のテスト"""
        with self.collector.track_node("test_node", "llm"):
            time.sleep(0.01)
        
        metrics_text = self.collector.get_metrics().decode('utf-8')
        assert "langgraph_node_executions_total" in metrics_text
    
    def test_get_metrics_text(self):
        """メトリクステキスト取得のテスト"""
        self.collector.llm_requests_total.labels(
            provider="gemini",
            model="test-model",
            method="generate"
        ).inc()
        
        metrics_text = get_metrics_text()
        
        assert isinstance(metrics_text, str)
        assert len(metrics_text) > 0


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required packages not installed")
class TestMetricsDecorator:
    """メトリクスデコレーターのテスト"""
    
    @pytest.mark.asyncio
    async def test_track_metrics_decorator_async(self):
        """非同期関数のメトリクスデコレーターテスト"""
        @track_metrics('llm', provider='gemini', model='test-model', method='generate')
        async def test_function():
            return "test"
        
        result = await test_function()
        assert result == "test"
    
    def test_track_metrics_decorator_sync(self):
        """同期関数のメトリクスデコレーターテスト"""
        @track_metrics('workflow', workflow_name='test_workflow')
        def test_function():
            return "test"
        
        result = test_function()
        assert result == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

