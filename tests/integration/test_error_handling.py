"""Error Handling Integration Tests

エラーハンドリングのエンドツーエンドテスト。
様々なエラーケースをテストします。
"""

import pytest
from typing import Dict, Any

from src.workflows.atomic.chat import ChatWorkflow, ChatInput
from src.nodes.primitives.llm.gemini.node import LLMNode
from src.nodes.base import NodeState
from src.providers.llm.mock import MockLLMProvider
from src.core.exceptions import (
    ProviderError,
    NodeExecutionError,
    WorkflowExecutionError
)


class TestProviderErrors:
    """プロバイダーレベルのエラーハンドリング"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_provider_timeout_error(self):
        """プロバイダータイムアウトエラーのテスト"""
        import asyncio
        
        class TimeoutMockProvider(MockLLMProvider):
            async def generate(self, prompt: str, **kwargs):
                await asyncio.sleep(10)  # 長時間待機
                return "response"
        
        provider = TimeoutMockProvider()
        node = LLMNode(provider=provider)
        
        state = NodeState(messages=["test"])
        
        # タイムアウトを設定してテスト
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(node.execute(state), timeout=1.0)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_provider_authentication_error(self):
        """プロバイダー認証エラーのテスト"""
        class AuthErrorProvider(MockLLMProvider):
            async def generate(self, prompt: str, **kwargs):
                raise ProviderError(
                    "Authentication failed: Invalid API key",
                    details={"provider": "test", "error_code": "AUTH_001"}
                )
        
        provider = AuthErrorProvider()
        node = LLMNode(provider=provider)
        
        state = NodeState(messages=["test"])
        result = await node.execute(state)
        
        # エラーが適切にハンドリングされることを確認
        assert "error" in result.data
        assert "Authentication failed" in result.data["error"]
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_provider_rate_limit_error(self):
        """プロバイダーレート制限エラーのテスト"""
        class RateLimitProvider(MockLLMProvider):
            def __init__(self):
                super().__init__()
                self.call_count = 0
            
            async def generate(self, prompt: str, **kwargs):
                self.call_count += 1
                if self.call_count > 3:
                    raise ProviderError(
                        "Rate limit exceeded",
                        details={"retry_after": 60}
                    )
                return f"response {self.call_count}"
        
        provider = RateLimitProvider()
        node = LLMNode(provider=provider)
        
        # 複数回実行してレート制限に達する
        for i in range(5):
            state = NodeState(messages=[f"test {i}"])
            result = await node.execute(state)
            
            if i < 3:
                assert "llm_response" in result.data
            else:
                assert "error" in result.data
                assert "Rate limit" in result.data["error"]


class TestNodeErrors:
    """ノードレベルのエラーハンドリング"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_node_invalid_input_error(self):
        """ノード無効入力エラーのテスト"""
        provider = MockLLMProvider()
        node = LLMNode(provider=provider)
        
        # 空のステートを渡す
        state = NodeState()
        result = await node.execute(state)
        
        # 空のプロンプトでも処理は完了する（エラーにはならない）
        assert isinstance(result, NodeState)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_node_execution_exception(self):
        """ノード実行例外のテスト"""
        class ExceptionProvider(MockLLMProvider):
            async def generate(self, prompt: str, **kwargs):
                raise Exception("Unexpected error occurred")
        
        provider = ExceptionProvider()
        node = LLMNode(provider=provider)
        
        state = NodeState(messages=["test"])
        result = await node.execute(state)
        
        # 例外が適切にキャッチされることを確認
        assert "error" in result.data
        assert "Unexpected error" in result.data["error"]
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_node_memory_error(self):
        """ノードメモリエラーのテスト（シミュレーション）"""
        class MemoryErrorProvider(MockLLMProvider):
            async def generate(self, prompt: str, **kwargs):
                # 実際にはMemoryErrorを発生させるのは難しいのでシミュレート
                raise MemoryError("Out of memory")
        
        provider = MemoryErrorProvider()
        node = LLMNode(provider=provider)
        
        state = NodeState(messages=["test"])
        result = await node.execute(state)
        
        # メモリエラーもキャッチされることを確認
        assert "error" in result.data


class TestWorkflowErrors:
    """ワークフローレベルのエラーハンドリング"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_provider_failure(self):
        """ワークフロー内でのプロバイダー失敗のテスト"""
        class FailingProvider(MockLLMProvider):
            async def generate(self, prompt: str, **kwargs):
                raise ValueError("Provider initialization failed")
        
        provider = FailingProvider()
        workflow = ChatWorkflow(llm_provider=provider)
        
        result = await workflow.run(ChatInput(message="test"))
        
        # ワークフローがエラーを適切にハンドリングすることを確認
        assert result.success is False
        assert result.error_message
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_partial_failure(self):
        """ワークフローの部分的失敗のテスト"""
        call_count = {"count": 0}
        
        class PartialFailProvider(MockLLMProvider):
            async def generate(self, prompt: str, **kwargs):
                call_count["count"] += 1
                if call_count["count"] == 2:
                    raise ValueError("Second call failed")
                return f"response {call_count['count']}"
        
        provider = PartialFailProvider()
        workflow = ChatWorkflow(llm_provider=provider)
        
        # 1回目は成功
        result1 = await workflow.run(ChatInput(message="test1"))
        assert result1.success is True
        
        # 2回目は失敗
        result2 = await workflow.run(ChatInput(message="test2"))
        assert result2.success is False
        
        # 3回目は成功
        result3 = await workflow.run(ChatInput(message="test3"))
        assert result3.success is True
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_recovery_after_error(self):
        """エラー後のワークフロー回復テスト"""
        provider = MockLLMProvider()
        workflow = ChatWorkflow(llm_provider=provider)
        
        # 通常の実行
        result1 = await workflow.run(ChatInput(message="test1"))
        assert result1.success is True
        
        # エラーを起こすプロバイダーに置き換え
        class ErrorProvider(MockLLMProvider):
            async def generate(self, prompt: str, **kwargs):
                raise ValueError("Temporary error")
        
        workflow.llm_node.provider = ErrorProvider()
        result2 = await workflow.run(ChatInput(message="test2"))
        assert result2.success is False
        
        # 正常なプロバイダーに戻す
        workflow.llm_node.provider = provider
        result3 = await workflow.run(ChatInput(message="test3"))
        assert result3.success is True


class TestErrorPropagation:
    """エラー伝播のテスト"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_context_preservation(self):
        """エラーコンテキスト保持のテスト"""
        class DetailedErrorProvider(MockLLMProvider):
            async def generate(self, prompt: str, **kwargs):
                raise ProviderError(
                    "Detailed error message",
                    details={
                        "error_code": "ERR_001",
                        "timestamp": "2025-11-22T10:00:00Z",
                        "request_id": "req_123"
                    }
                )
        
        provider = DetailedErrorProvider()
        node = LLMNode(provider=provider)
        
        state = NodeState(messages=["test"])
        state.metadata["original_request_id"] = "original_123"
        
        result = await node.execute(state)
        
        # オリジナルのメタデータが保持されることを確認
        assert result.metadata["original_request_id"] == "original_123"
        assert "error" in result.data
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_nested_error_handling(self):
        """ネストされたエラーハンドリングのテスト"""
        class NestedErrorProvider(MockLLMProvider):
            async def generate(self, prompt: str, **kwargs):
                try:
                    raise ValueError("Inner error")
                except ValueError as e:
                    raise RuntimeError("Outer error") from e
        
        provider = NestedErrorProvider()
        node = LLMNode(provider=provider)
        
        state = NodeState(messages=["test"])
        result = await node.execute(state)
        
        # ネストされたエラーが適切にハンドリングされることを確認
        assert "error" in result.data
        assert "Outer error" in result.data["error"]


@pytest.mark.integration
class TestErrorRecovery:
    """エラー回復のテスト"""
    
    @pytest.mark.asyncio
    async def test_retry_mechanism(self):
        """リトライメカニズムのテスト"""
        attempt_count = {"count": 0}
        
        class RetryableProvider(MockLLMProvider):
            async def generate(self, prompt: str, **kwargs):
                attempt_count["count"] += 1
                if attempt_count["count"] < 3:
                    raise ValueError("Temporary failure")
                return "success after retries"
        
        provider = RetryableProvider()
        
        # リトライロジックを実装
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                node = LLMNode(provider=provider)
                state = NodeState(messages=["test"])
                result = await node.execute(state)
                
                if "llm_response" in result.data:
                    break
                
                last_error = result.data.get("error")
            except Exception as e:
                last_error = str(e)
        
        # 最終的に成功することを確認
        assert attempt_count["count"] == 3
        assert "llm_response" in result.data
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """グレースフルデグラデーションのテスト"""
        class DegradedProvider(MockLLMProvider):
            def __init__(self):
                super().__init__()
                self.degraded_mode = False
            
            async def generate(self, prompt: str, **kwargs):
                if self.degraded_mode:
                    return "simplified response (degraded mode)"
                raise ValueError("Primary service unavailable")
        
        provider = DegradedProvider()
        node = LLMNode(provider=provider)
        
        state = NodeState(messages=["test"])
        
        # 最初は失敗
        result1 = await node.execute(state)
        assert "error" in result1.data
        
        # デグレードモードに切り替え
        provider.degraded_mode = True
        result2 = await node.execute(state)
        
        # デグレードモードで成功
        assert "llm_response" in result2.data
        assert "degraded mode" in result2.data["llm_response"]

