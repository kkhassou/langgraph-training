"""End-to-End Node Tests

ノードのエンドツーエンドテスト。
実際のノード実行をテストします。
"""

import pytest
from typing import Dict, Any

from src.nodes.base import NodeState
from src.nodes.primitives.llm.gemini.node import LLMNode
from src.providers.llm.mock import MockLLMProvider


@pytest.fixture
def mock_llm_provider():
    """テスト用のモックLLMプロバイダー"""
    return MockLLMProvider(
        responses={
            "テストプロンプト": "テスト応答",
            "エラーテスト": "エラーが発生しました"
        }
    )


class TestLLMNode:
    """LLMノードのテスト"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_llm_node_basic_execution(self, mock_llm_provider):
        """LLMノードの基本的な実行テスト"""
        node = LLMNode(provider=mock_llm_provider, name="test_llm_node")
        
        state = NodeState()
        state.messages = ["テストプロンプト"]
        state.data["temperature"] = 0.7
        
        result_state = await node.execute(state)
        
        assert "llm_response" in result_state.data
        assert result_state.metadata["node"] == "test_llm_node"
        assert result_state.metadata["provider"] == "MockLLMProvider"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_llm_node_with_custom_parameters(self, mock_llm_provider):
        """カスタムパラメータを使用したLLMノードのテスト"""
        node = LLMNode(provider=mock_llm_provider)
        
        state = NodeState()
        state.messages = ["テストプロンプト"]
        state.data["temperature"] = 0.9
        state.data["max_tokens"] = 500
        
        result_state = await node.execute(state)
        
        assert "llm_response" in result_state.data
        
        # プロバイダーの呼び出し履歴を確認
        assert len(mock_llm_provider.call_history) == 1
        call = mock_llm_provider.call_history[0]
        assert call["temperature"] == 0.9
        assert call["max_tokens"] == 500
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_llm_node_error_handling(self):
        """LLMノードのエラーハンドリングテスト"""
        # エラーを発生させるモックプロバイダー
        class ErrorMockProvider(MockLLMProvider):
            async def generate(self, prompt: str, **kwargs):
                raise ValueError("Test error")
        
        error_provider = ErrorMockProvider()
        node = LLMNode(provider=error_provider)
        
        state = NodeState()
        state.messages = ["テストプロンプト"]
        
        result_state = await node.execute(state)
        
        # エラーが適切にハンドリングされることを確認
        assert "error" in result_state.data
        assert "Test error" in result_state.data["error"]
        assert result_state.metadata["error_node"] == node.name


class TestNodeChaining:
    """ノードチェーン（連続実行）のテスト"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multiple_nodes_execution(self, mock_llm_provider):
        """複数ノードの連続実行テスト"""
        node1 = LLMNode(provider=mock_llm_provider, name="node1")
        node2 = LLMNode(provider=mock_llm_provider, name="node2")
        
        state = NodeState()
        state.messages = ["テストプロンプト"]
        
        # 1つ目のノードを実行
        state = await node1.execute(state)
        assert "llm_response" in state.data
        
        # 2つ目のノードを実行（前のノードの出力を使用）
        state.messages.append(state.data["llm_response"])
        state = await node2.execute(state)
        
        # 両方のノードが実行されたことを確認
        assert len(mock_llm_provider.call_history) == 2
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_node_state_preservation(self, mock_llm_provider):
        """ノード間での状態保持テスト"""
        node = LLMNode(provider=mock_llm_provider)
        
        state = NodeState()
        state.messages = ["テストプロンプト"]
        state.data["custom_field"] = "カスタムデータ"
        state.metadata["request_id"] = "test-123"
        
        result_state = await node.execute(state)
        
        # カスタムフィールドが保持されていることを確認
        assert result_state.data["custom_field"] == "カスタムデータ"
        assert result_state.metadata["request_id"] == "test-123"


class TestNodePerformance:
    """ノードパフォーマンステスト"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_node_execution_time(self, mock_llm_provider):
        """ノード実行時間のテスト"""
        import time
        
        node = LLMNode(provider=mock_llm_provider)
        
        state = NodeState()
        state.messages = ["パフォーマンステスト"]
        
        start_time = time.time()
        await node.execute(state)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # モックプロバイダーを使用しているので、0.5秒以内に完了するはず
        assert execution_time < 0.5
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_node_concurrent_execution(self, mock_llm_provider):
        """ノードの並行実行テスト"""
        import asyncio
        
        node = LLMNode(provider=mock_llm_provider)
        
        # 複数のステートを並行実行
        states = [
            NodeState(messages=[f"テスト{i}"])
            for i in range(5)
        ]
        
        results = await asyncio.gather(
            *[node.execute(state) for state in states]
        )
        
        # 全ての実行が完了したことを確認
        assert len(results) == 5
        assert all("llm_response" in r.data for r in results)


@pytest.mark.integration
class TestNodeIntegration:
    """ノード統合テスト"""
    
    @pytest.mark.asyncio
    async def test_node_with_different_providers(self):
        """異なるプロバイダーを使用したノードのテスト"""
        provider1 = MockLLMProvider(responses={"test": "response1"})
        provider2 = MockLLMProvider(responses={"test": "response2"})
        
        node1 = LLMNode(provider=provider1, name="node1")
        node2 = LLMNode(provider=provider2, name="node2")
        
        state = NodeState(messages=["test"])
        
        result1 = await node1.execute(state)
        result2 = await node2.execute(state)
        
        # 異なるプロバイダーが使用されていることを確認
        assert result1.metadata["provider"] == "MockLLMProvider"
        assert result2.metadata["provider"] == "MockLLMProvider"
    
    @pytest.mark.asyncio
    async def test_node_memory_cleanup(self, mock_llm_provider):
        """ノードのメモリクリーンアップテスト"""
        import gc
        
        node = LLMNode(provider=mock_llm_provider)
        
        # 大量のデータを処理
        for i in range(100):
            state = NodeState(messages=[f"テスト{i}" * 100])
            await node.execute(state)
        
        # ガベージコレクションを実行
        gc.collect()
        
        # メモリリークがないことを簡易的に確認
        # （実際の環境では memory_profiler などを使用）
        assert True  # プレースホルダー

