"""DIコンテナのテスト"""

import pytest
from src.core.containers import Container, get_container, reset_container, get_llm_provider
from src.core.providers.llm import LLMProvider
from src.providers.llm.gemini import GeminiProvider
from src.providers.llm.mock import MockLLMProvider


class TestDIContainer:
    """DIコンテナのテストクラス"""
    
    def setup_method(self):
        """各テストの前にコンテナをリセット"""
        reset_container()
    
    def test_container_creation(self):
        """コンテナの作成テスト"""
        container = Container()
        assert container is not None
        assert hasattr(container, 'llm_provider')
        assert hasattr(container, 'rag_provider')
    
    def test_gemini_provider_creation(self):
        """Geminiプロバイダーの作成テスト"""
        container = Container()
        container.config.from_dict({
            'llm_provider_type': 'gemini',
            'gemini': {
                'api_key': 'test-api-key',
                'model': 'gemini-2.0-flash-exp'
            }
        })
        
        provider = container.llm_provider()
        assert isinstance(provider, GeminiProvider)
        assert provider.api_key == 'test-api-key'
        assert provider.model == 'gemini-2.0-flash-exp'
    
    def test_mock_provider_creation(self):
        """Mockプロバイダーの作成テスト"""
        container = Container()
        container.config.from_dict({
            'llm_provider_type': 'mock',
            'mock': {
                'responses': {
                    'Hello': 'Hi there!'
                }
            }
        })
        
        provider = container.llm_provider()
        assert isinstance(provider, MockLLMProvider)
        assert 'Hello' in provider.responses
    
    def test_provider_switching(self):
        """プロバイダーの動的切り替えテスト"""
        container = Container()
        
        # Geminiプロバイダー
        container.config.from_dict({
            'llm_provider_type': 'gemini',
            'gemini': {'api_key': 'test-key', 'model': 'gemini-2.0-flash-exp'}
        })
        provider1 = container.llm_provider()
        assert isinstance(provider1, GeminiProvider)
        
        # Mockプロバイダーに切り替え
        container.config.llm_provider_type.from_value('mock')
        provider2 = container.llm_provider()
        assert isinstance(provider2, MockLLMProvider)
    
    def test_singleton_behavior(self):
        """シングルトンの動作テスト"""
        container = Container()
        container.config.from_dict({
            'llm_provider_type': 'gemini',
            'gemini': {'api_key': 'test-key', 'model': 'gemini-2.0-flash-exp'}
        })
        
        provider1 = container.gemini_provider()
        provider2 = container.gemini_provider()
        
        # 同じインスタンスが返される
        assert provider1 is provider2
    
    def test_global_container(self):
        """グローバルコンテナのテスト"""
        container1 = get_container()
        container2 = get_container()
        
        # 同じインスタンスが返される
        assert container1 is container2
    
    def test_get_llm_provider_convenience_function(self):
        """便利関数get_llm_providerのテスト"""
        reset_container()
        
        # デフォルト（Gemini）
        provider = get_llm_provider()
        assert isinstance(provider, LLMProvider)
    
    def test_workflow_creation_with_di(self):
        """DIコンテナを使用したワークフロー作成テスト"""
        container = Container()
        container.config.from_dict({
            'llm_provider_type': 'mock',
            'mock': {'responses': {'test': 'response'}}
        })
        
        # ChatWorkflowを作成（依存性は自動注入）
        workflow = container.chat_workflow()
        assert workflow is not None
        assert hasattr(workflow, 'llm_node')
        
        # 注入されたプロバイダーがMockであることを確認
        assert isinstance(workflow.llm_node.provider, MockLLMProvider)
    
    def test_node_creation_with_di(self):
        """DIコンテナを使用したノード作成テスト"""
        container = Container()
        container.config.from_dict({
            'llm_provider_type': 'mock',
            'mock': {'responses': {}}
        })
        
        # TodoAdvisorNodeを作成
        node = container.todo_advisor_node()
        assert node is not None
        assert hasattr(node, 'provider')
        assert isinstance(node.provider, MockLLMProvider)
    
    def test_config_override(self):
        """設定のオーバーライドテスト"""
        container = Container()
        
        # デフォルト設定
        container.config.from_dict({
            'llm_provider_type': 'gemini',
            'gemini': {'api_key': 'key1', 'model': 'model1'}
        })
        provider1 = container.gemini_provider()
        assert provider1.api_key == 'key1'
        
        # 設定をリセットして新しいコンテナを作成
        container2 = Container()
        container2.config.from_dict({
            'llm_provider_type': 'gemini',
            'gemini': {'api_key': 'key2', 'model': 'model2'}
        })
        provider2 = container2.gemini_provider()
        assert provider2.api_key == 'key2'
    
    def test_container_isolation(self):
        """コンテナの独立性テスト"""
        container1 = Container()
        container1.config.from_dict({
            'llm_provider_type': 'gemini',
            'gemini': {'api_key': 'key1', 'model': 'model1'}
        })
        
        container2 = Container()
        container2.config.from_dict({
            'llm_provider_type': 'mock',
            'mock': {'responses': {}}
        })
        
        provider1 = container1.llm_provider()
        provider2 = container2.llm_provider()
        
        # 異なるプロバイダーが返される
        assert type(provider1) != type(provider2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

