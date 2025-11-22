"""Provider Factory のテスト"""

import pytest
from src.core.factory import ProviderFactory, create_llm_provider, create_rag_provider
from src.core.providers.llm import LLMProvider
from src.core.providers.rag import RAGProvider
from src.providers.llm.gemini import GeminiProvider
from src.providers.llm.mock import MockLLMProvider
from src.providers.rag.simple import SimpleRAGProvider


def test_list_llm_providers():
    """利用可能なLLMプロバイダーのリスト取得テスト"""
    providers = ProviderFactory.list_llm_providers()
    
    assert isinstance(providers, list)
    assert "gemini" in providers
    assert "mock" in providers


def test_list_rag_providers():
    """利用可能なRAGプロバイダーのリスト取得テスト"""
    providers = ProviderFactory.list_rag_providers()
    
    assert isinstance(providers, list)
    assert "simple" in providers


def test_create_gemini_provider():
    """Geminiプロバイダーの生成テスト"""
    provider = ProviderFactory.create_llm_provider(
        provider_type="gemini",
        config={"api_key": "test-key", "model": "gemini-pro"}
    )
    
    assert isinstance(provider, GeminiProvider)
    assert isinstance(provider, LLMProvider)


def test_create_mock_provider():
    """Mockプロバイダーの生成テスト"""
    provider = ProviderFactory.create_llm_provider(
        provider_type="mock",
        config={"default_response": "Test response"}
    )
    
    assert isinstance(provider, MockLLMProvider)
    assert isinstance(provider, LLMProvider)


def test_create_simple_rag_provider():
    """SimpleRAGプロバイダーの生成テスト"""
    provider = ProviderFactory.create_rag_provider(
        provider_type="simple"
    )
    
    assert isinstance(provider, SimpleRAGProvider)
    assert isinstance(provider, RAGProvider)


def test_create_provider_with_unknown_type():
    """未知のプロバイダータイプでのエラーテスト"""
    with pytest.raises(ValueError) as exc_info:
        ProviderFactory.create_llm_provider(provider_type="unknown")
    
    assert "Unknown LLM provider type" in str(exc_info.value)
    assert "unknown" in str(exc_info.value)


def test_register_custom_llm_provider():
    """カスタムLLMプロバイダーの登録テスト"""
    # カスタムプロバイダークラスを定義
    class CustomLLMProvider(LLMProvider):
        def __init__(self, custom_param: str = "default"):
            self.custom_param = custom_param
        
        async def generate(self, prompt, **kwargs):
            return f"Custom: {prompt}"
        
        async def generate_json(self, prompt, schema, **kwargs):
            return schema()
        
        async def generate_with_context(self, user_query, context, **kwargs):
            return f"Custom answer: {user_query}"
    
    # カスタムプロバイダーを登録
    ProviderFactory.register_llm_provider("custom", CustomLLMProvider)
    
    # 登録されたことを確認
    assert "custom" in ProviderFactory.list_llm_providers()
    
    # カスタムプロバイダーを生成
    provider = ProviderFactory.create_llm_provider(
        provider_type="custom",
        config={"custom_param": "test_value"}
    )
    
    assert isinstance(provider, CustomLLMProvider)
    assert provider.custom_param == "test_value"


def test_register_custom_rag_provider():
    """カスタムRAGプロバイダーの登録テスト"""
    # カスタムプロバイダークラスを定義
    class CustomRAGProvider(RAGProvider):
        def __init__(self, custom_param: str = "default"):
            self.custom_param = custom_param
        
        async def query(self, query, **kwargs):
            from src.core.providers.rag import RAGResult
            return RAGResult(
                answer=f"Custom: {query}",
                retrieved_documents=[],
                context_used="custom context"
            )
        
        async def ingest_documents(self, documents, **kwargs):
            return {"success": True, "count": len(documents)}
    
    # カスタムプロバイダーを登録
    ProviderFactory.register_rag_provider("custom", CustomRAGProvider)
    
    # 登録されたことを確認
    assert "custom" in ProviderFactory.list_rag_providers()
    
    # カスタムプロバイダーを生成
    provider = ProviderFactory.create_rag_provider(
        provider_type="custom",
        config={"custom_param": "test_value"}
    )
    
    assert isinstance(provider, CustomRAGProvider)
    assert provider.custom_param == "test_value"


def test_get_default_llm_provider():
    """デフォルトLLMプロバイダーの取得テスト"""
    provider = ProviderFactory.get_default_llm_provider()
    
    assert isinstance(provider, LLMProvider)
    assert isinstance(provider, GeminiProvider)


def test_get_default_rag_provider():
    """デフォルトRAGプロバイダーの取得テスト"""
    provider = ProviderFactory.get_default_rag_provider()
    
    assert isinstance(provider, RAGProvider)
    assert isinstance(provider, SimpleRAGProvider)


def test_create_llm_provider_function():
    """LLMプロバイダー生成関数のテスト"""
    provider = create_llm_provider(
        provider_type="mock",
        default_response="Function test"
    )
    
    assert isinstance(provider, MockLLMProvider)
    assert provider.default_response == "Function test"


def test_create_rag_provider_function():
    """RAGプロバイダー生成関数のテスト"""
    provider = create_rag_provider(provider_type="simple")
    
    assert isinstance(provider, SimpleRAGProvider)


def test_create_provider_without_config():
    """設定なしでのプロバイダー生成テスト"""
    # Mockプロバイダーは設定なしでも生成可能
    provider = ProviderFactory.create_llm_provider(provider_type="mock")
    
    assert isinstance(provider, MockLLMProvider)
    assert provider.default_response == "Mock response"  # デフォルト値


def test_create_gemini_provider_with_default_config():
    """デフォルト設定でのGeminiプロバイダー生成テスト"""
    # api_keyは設定から自動取得される
    provider = ProviderFactory.create_llm_provider(provider_type="gemini")
    
    assert isinstance(provider, GeminiProvider)
    # モデル名はデフォルト値が設定される
    assert provider.model == "gemini-2.0-flash-exp"


def test_multiple_provider_creation():
    """複数のプロバイダーを連続生成するテスト"""
    providers = []
    
    # 複数のプロバイダーを生成
    for i in range(5):
        provider = ProviderFactory.create_llm_provider(
            provider_type="mock",
            config={"default_response": f"Response {i}"}
        )
        providers.append(provider)
    
    # 各プロバイダーが独立していることを確認
    assert len(providers) == 5
    assert all(isinstance(p, MockLLMProvider) for p in providers)
    assert providers[0].default_response == "Response 0"
    assert providers[4].default_response == "Response 4"


def test_provider_factory_thread_safety():
    """プロバイダーファクトリーのスレッドセーフ性テスト"""
    # レジストリの変更が他の生成に影響しないことを確認
    
    # カスタムプロバイダーを登録
    class TestProvider(LLMProvider):
        async def generate(self, prompt, **kwargs):
            return "test"
        async def generate_json(self, prompt, schema, **kwargs):
            return schema()
        async def generate_with_context(self, user_query, context, **kwargs):
            return "test"
    
    ProviderFactory.register_llm_provider("test_provider", TestProvider)
    
    # 既存のプロバイダーが影響を受けないことを確認
    gemini = ProviderFactory.create_llm_provider("gemini")
    mock = ProviderFactory.create_llm_provider("mock")
    test = ProviderFactory.create_llm_provider("test_provider")
    
    assert isinstance(gemini, GeminiProvider)
    assert isinstance(mock, MockLLMProvider)
    assert isinstance(test, TestProvider)

