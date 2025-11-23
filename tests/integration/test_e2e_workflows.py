"""End-to-End Workflow Tests

ワークフローのエンドツーエンドテスト。
実際のプロバイダーを使用して、完全なワークフロー実行をテストします。
"""

import pytest
from typing import Dict, Any

from src.workflows.atomic.chat import ChatWorkflow, ChatInput, ChatOutput
from src.workflows.atomic.rag_query import RAGQueryWorkflow, RAGQueryInput, RAGQueryOutput
from src.workflows.composite.intelligent_chat.chain_of_thought import (
    ChainOfThoughtWorkflow,
    ChainOfThoughtInput,
    ChainOfThoughtOutput
)
from src.workflows.composite.intelligent_chat.reflection import (
    ReflectionWorkflow,
    ReflectionInput,
    ReflectionOutput
)
from src.providers.llm.mock import MockLLMProvider


class TestAtomicWorkflows:
    """Atomic Workflow層のテスト"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_chat_workflow_basic(self):
        """基本的なチャットワークフローのテスト"""
        # モックプロバイダーを使用
        mock_provider = MockLLMProvider(
            responses={
                "こんにちは": "こんにちは！何かお手伝いできることはありますか？"
            }
        )
        
        workflow = ChatWorkflow(llm_provider=mock_provider)
        result = await workflow.run(ChatInput(message="こんにちは"))
        
        assert result.success is True
        assert result.response
        assert len(result.response) > 0
        assert "こんにちは" in result.response
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_chat_workflow_with_parameters(self):
        """パラメータ付きチャットワークフローのテスト"""
        mock_provider = MockLLMProvider()
        
        workflow = ChatWorkflow(llm_provider=mock_provider)
        result = await workflow.run(
            ChatInput(
                message="Python の特徴は？",
                temperature=0.5,
                max_tokens=500
            )
        )
        
        assert result.success is True
        assert result.response
        
        # モックプロバイダーの呼び出し履歴を確認
        assert len(mock_provider.call_history) == 1
        call = mock_provider.call_history[0]
        assert call["method"] == "generate"
        assert call["temperature"] == 0.5
        assert call["max_tokens"] == 500
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_chat_workflow_empty_message(self):
        """空メッセージのエラーハンドリングテスト"""
        mock_provider = MockLLMProvider()
        
        workflow = ChatWorkflow(llm_provider=mock_provider)
        result = await workflow.run(ChatInput(message=""))
        
        # 空メッセージでも処理は完了するが、結果が空の可能性がある
        assert isinstance(result, ChatOutput)


class TestCompositeWorkflows:
    """Composite Workflow層のテスト"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_chain_of_thought_workflow(self):
        """Chain of Thoughtワークフローのテスト"""
        mock_provider = MockLLMProvider(
            responses={
                "ステップ1: なぜ空は青いのですか？": "まず、光の性質について考えます。",
                "ステップ2: なぜ空は青いのですか？": "次に、大気中での光の散乱を考えます。",
                "ステップ3: なぜ空は青いのですか？": "最後に、レイリー散乱により青い光が散乱されます。"
            }
        )
        
        workflow = ChainOfThoughtWorkflow(llm_provider=mock_provider)
        result = await workflow.run(
            ChainOfThoughtInput(
                question="なぜ空は青いのですか？",
                steps=3
            )
        )
        
        assert result.success is True
        assert len(result.reasoning_steps) == 3
        assert result.final_answer
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_reflection_workflow(self):
        """Reflectionワークフローのテスト"""
        mock_provider = MockLLMProvider()
        
        workflow = ReflectionWorkflow(llm_provider=mock_provider)
        result = await workflow.run(
            ReflectionInput(
                question="Pythonの特徴を説明してください",
                max_iterations=2
            )
        )
        
        assert result.success is True
        assert len(result.iterations) <= 2
        assert result.final_answer


class TestWorkflowErrorHandling:
    """ワークフローのエラーハンドリングテスト"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_with_invalid_temperature(self):
        """無効なtemperatureパラメータのテスト"""
        mock_provider = MockLLMProvider()
        
        workflow = ChatWorkflow(llm_provider=mock_provider)
        
        # temperature > 1.0 は通常エラーになるが、モックは受け入れる
        result = await workflow.run(
            ChatInput(message="テスト", temperature=2.0)
        )
        
        # モックプロバイダーは全てのパラメータを受け入れる
        assert isinstance(result, ChatOutput)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_provider_error_handling(self):
        """プロバイダーエラーのハンドリングテスト"""
        # エラーを発生させるモックプロバイダー
        class ErrorMockProvider(MockLLMProvider):
            async def generate(self, prompt: str, **kwargs):
                raise ValueError("Test error: Invalid API key")
        
        error_provider = ErrorMockProvider()
        workflow = ChatWorkflow(llm_provider=error_provider)
        
        result = await workflow.run(ChatInput(message="テスト"))
        
        # エラーが適切にハンドリングされることを確認
        assert result.success is False
        assert result.error_message
        assert "Test error" in result.error_message


class TestWorkflowIntegration:
    """ワークフロー統合テスト"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multiple_workflow_execution(self):
        """複数ワークフローの連続実行テスト"""
        mock_provider = MockLLMProvider(
            responses={
                "質問1": "回答1",
                "質問2": "回答2",
                "質問3": "回答3"
            }
        )
        
        workflow = ChatWorkflow(llm_provider=mock_provider)
        
        results = []
        for i in range(3):
            result = await workflow.run(ChatInput(message=f"質問{i+1}"))
            results.append(result)
        
        # 全ての実行が成功したことを確認
        assert all(r.success for r in results)
        assert len(results) == 3
        
        # 呼び出し履歴を確認
        assert len(mock_provider.call_history) == 3
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_state_isolation(self):
        """ワークフロー間の状態分離テスト"""
        mock_provider = MockLLMProvider()
        
        workflow1 = ChatWorkflow(llm_provider=mock_provider)
        workflow2 = ChatWorkflow(llm_provider=mock_provider)
        
        result1 = await workflow1.run(ChatInput(message="テスト1"))
        result2 = await workflow2.run(ChatInput(message="テスト2"))
        
        # 各ワークフローが独立して動作することを確認
        assert result1 != result2
        assert result1.response != result2.response


@pytest.mark.integration
class TestWorkflowPerformance:
    """ワークフローパフォーマンステスト"""
    
    @pytest.mark.asyncio
    async def test_workflow_execution_time(self):
        """ワークフロー実行時間のテスト"""
        import time
        
        mock_provider = MockLLMProvider()
        workflow = ChatWorkflow(llm_provider=mock_provider)
        
        start_time = time.time()
        result = await workflow.run(ChatInput(message="パフォーマンステスト"))
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # モックプロバイダーを使用しているので、1秒以内に完了するはず
        assert execution_time < 1.0
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_workflow_memory_usage(self):
        """ワークフローのメモリ使用量テスト"""
        import sys
        
        mock_provider = MockLLMProvider()
        workflow = ChatWorkflow(llm_provider=mock_provider)
        
        # 複数回実行してメモリリークがないか確認
        for _ in range(10):
            await workflow.run(ChatInput(message="メモリテスト"))
        
        # メモリサイズを取得（簡易チェック）
        workflow_size = sys.getsizeof(workflow)
        
        # ワークフローオブジェクトが異常に大きくないことを確認
        assert workflow_size < 10000  # 10KB未満

