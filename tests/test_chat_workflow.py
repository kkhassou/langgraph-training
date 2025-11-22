"""Chat Workflow のテスト"""

import pytest
from src.workflows.atomic.chat import ChatWorkflow, ChatInput
from src.providers.llm.mock import MockLLMProvider
from src.core.factory import ProviderFactory


@pytest.mark.asyncio
async def test_chat_workflow_basic():
    """基本的なチャットフローのテスト"""
    # ✅ モックプロバイダーを注入
    mock_provider = MockLLMProvider(
        responses={
            "Hello": "Hi there! How can I help you today?"
        }
    )

    workflow = ChatWorkflow(llm_provider=mock_provider)
    result = await workflow.run(ChatInput(message="Hello"))

    # 検証
    assert result.success is True
    assert "Hi there" in result.response
    assert len(mock_provider.call_history) == 1
    assert mock_provider.call_history[0]["prompt"] == "Hello"


@pytest.mark.asyncio
async def test_chat_workflow_with_parameters():
    """パラメータ付きテスト"""
    mock_provider = MockLLMProvider()
    workflow = ChatWorkflow(llm_provider=mock_provider)

    await workflow.run(
        ChatInput(message="Test", temperature=0.9, max_tokens=500)
    )

    # モックの呼び出し履歴を確認
    call = mock_provider.call_history[0]
    assert call["temperature"] == 0.9
    assert call["max_tokens"] == 500


@pytest.mark.asyncio
async def test_chat_workflow_default_provider():
    """デフォルトプロバイダーでのテスト（実際のAPI呼び出しなし）"""
    # デフォルトではGeminiProviderが使用されるが、
    # テスト環境ではAPI_KEYがないとエラーになる可能性があるため、
    # モックプロバイダーで代替
    mock_provider = MockLLMProvider(
        default_response="Default mock response"
    )
    
    workflow = ChatWorkflow(llm_provider=mock_provider)
    result = await workflow.run(ChatInput(message="Any question"))

    assert result.success is True
    assert "mock response" in result.response.lower()


@pytest.mark.asyncio
async def test_chat_workflow_with_factory():
    """ファクトリーパターンを使ったテスト"""
    # ファクトリーでモックプロバイダーを生成
    provider = ProviderFactory.create_llm_provider(
        provider_type="mock",
        config={
            "responses": {
                "What is AI?": "AI is artificial intelligence."
            }
        }
    )

    workflow = ChatWorkflow(llm_provider=provider)
    result = await workflow.run(ChatInput(message="What is AI?"))

    assert result.success is True
    assert "artificial intelligence" in result.response


@pytest.mark.asyncio
async def test_chat_workflow_error_handling():
    """エラーハンドリングのテスト"""
    # エラーを投げるモックプロバイダー
    class ErrorProvider(MockLLMProvider):
        async def generate(self, prompt, **kwargs):
            raise Exception("Simulated error")
    
    workflow = ChatWorkflow(llm_provider=ErrorProvider())
    result = await workflow.run(ChatInput(message="Test"))

    # エラーが適切にハンドリングされることを確認
    assert result.success is False
    assert result.error_message != ""
    assert "error" in result.error_message.lower()


@pytest.mark.asyncio
async def test_chat_workflow_multiple_calls():
    """複数回の呼び出しテスト"""
    mock_provider = MockLLMProvider(
        responses={
            "First": "Response 1",
            "Second": "Response 2",
            "Third": "Response 3"
        }
    )

    workflow = ChatWorkflow(llm_provider=mock_provider)

    # 複数回実行
    result1 = await workflow.run(ChatInput(message="First"))
    result2 = await workflow.run(ChatInput(message="Second"))
    result3 = await workflow.run(ChatInput(message="Third"))

    # 各結果を検証
    assert result1.success and "Response 1" in result1.response
    assert result2.success and "Response 2" in result2.response
    assert result3.success and "Response 3" in result3.response

    # 呼び出し履歴を確認
    assert len(mock_provider.call_history) == 3
    assert mock_provider.get_call_count("generate") == 3


@pytest.mark.asyncio
async def test_chat_workflow_temperature_variation():
    """異なる温度パラメータのテスト"""
    mock_provider = MockLLMProvider()
    workflow = ChatWorkflow(llm_provider=mock_provider)

    # 低温度（より決定的）
    await workflow.run(ChatInput(message="Test", temperature=0.1))
    low_temp_call = mock_provider.call_history[-1]

    # 高温度（より創造的）
    await workflow.run(ChatInput(message="Test", temperature=0.9))
    high_temp_call = mock_provider.call_history[-1]

    assert low_temp_call["temperature"] == 0.1
    assert high_temp_call["temperature"] == 0.9


@pytest.mark.asyncio
async def test_chat_workflow_mermaid_diagram():
    """Mermaid図の生成テスト"""
    mock_provider = MockLLMProvider()
    workflow = ChatWorkflow(llm_provider=mock_provider)

    # Mermaid図を取得
    diagram = workflow.get_mermaid_diagram()

    # 基本的な構造を確認
    assert diagram is not None
    assert isinstance(diagram, str)
    assert len(diagram) > 0


@pytest.mark.asyncio
async def test_chat_workflow_long_message():
    """長いメッセージのテスト"""
    mock_provider = MockLLMProvider(
        default_response="Understood your long message"
    )
    workflow = ChatWorkflow(llm_provider=mock_provider)

    # 長いメッセージを作成
    long_message = "This is a test message. " * 100

    result = await workflow.run(ChatInput(message=long_message))

    assert result.success is True
    # モックが呼び出されたことを確認
    assert len(mock_provider.call_history) == 1
    assert len(mock_provider.call_history[0]["prompt"]) > 1000

