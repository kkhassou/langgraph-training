"""プラグインローダーのテスト"""

import pytest
from pathlib import Path
from src.core.plugin_loader import (
    PluginLoader,
    PluginMetadata,
    LoadedPlugin,
    get_plugin_loader,
    auto_load_plugins
)
from src.core.providers.llm import LLMProvider
from src.core.exceptions import PluginLoadError, PluginValidationError


class TestPluginMetadata:
    """PluginMetadata のテスト"""
    
    def test_plugin_metadata_creation(self):
        """メタデータの作成テスト"""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            author="Test Author",
            description="Test Description",
            provider_type="llm"
        )
        
        assert metadata.name == "test_plugin"
        assert metadata.version == "1.0.0"
        assert metadata.provider_type == "llm"
        assert metadata.enabled is True
        assert metadata.dependencies == []
    
    def test_plugin_metadata_with_dependencies(self):
        """依存関係付きメタデータのテスト"""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            author="Test Author",
            description="Test Description",
            provider_type="llm",
            dependencies=["package1>=1.0.0", "package2"]
        )
        
        assert len(metadata.dependencies) == 2
        assert "package1>=1.0.0" in metadata.dependencies
    
    def test_invalid_provider_type(self):
        """不正なプロバイダータイプのテスト"""
        with pytest.raises(ValueError):
            PluginMetadata(
                name="test_plugin",
                version="1.0.0",
                author="Test Author",
                description="Test Description",
                provider_type="invalid"  # 不正な型
            )


class TestPluginLoader:
    """PluginLoader のテスト"""
    
    def test_plugin_loader_initialization(self):
        """PluginLoaderの初期化テスト"""
        loader = PluginLoader()
        
        assert loader.plugin_dir is not None
        assert isinstance(loader.plugin_dir, Path)
        assert loader.auto_register is True
        assert loader.loaded_plugins == []
    
    def test_discover_plugins(self):
        """プラグイン検出テスト"""
        loader = PluginLoader()
        plugins = loader.discover_plugins()
        
        # example_llm が検出されることを確認
        assert "example_llm" in plugins
    
    def test_load_example_plugin(self):
        """サンプルプラグインの読み込みテスト"""
        loader = PluginLoader(auto_register=False)
        
        plugin = loader.load_plugin("example_llm")
        
        assert plugin is not None
        assert plugin.loaded is True
        assert plugin.metadata.name == "example_llm"
        assert plugin.metadata.provider_type == "llm"
        assert plugin.provider_class is not None
        assert issubclass(plugin.provider_class, LLMProvider)
    
    def test_load_nonexistent_plugin(self):
        """存在しないプラグインの読み込みテスト"""
        loader = PluginLoader(auto_register=False)
        
        with pytest.raises(PluginLoadError):
            loader.load_plugin("nonexistent_plugin")
    
    def test_discover_and_register(self):
        """プラグインの検出と登録テスト"""
        loader = PluginLoader()
        plugins = loader.discover_and_register()
        
        assert len(plugins) > 0
        assert any(p.metadata.name == "example_llm" for p in plugins)
    
    def test_list_plugins(self):
        """プラグイン一覧取得テスト"""
        loader = PluginLoader()
        loader.discover_and_register()
        
        plugins = loader.list_plugins()
        
        assert len(plugins) > 0
        assert all(p.loaded for p in plugins)
    
    def test_get_plugin(self):
        """名前でプラグインを取得するテスト"""
        loader = PluginLoader()
        loader.discover_and_register()
        
        plugin = loader.get_plugin("example_llm")
        
        assert plugin is not None
        assert plugin.metadata.name == "example_llm"
    
    def test_get_nonexistent_plugin(self):
        """存在しないプラグインの取得テスト"""
        loader = PluginLoader()
        loader.discover_and_register()
        
        plugin = loader.get_plugin("nonexistent")
        
        assert plugin is None


class TestExampleLLMPlugin:
    """Example LLM プラグインのテスト"""
    
    async def test_example_llm_provider(self):
        """ExampleLLMProviderの動作テスト"""
        loader = PluginLoader(auto_register=False)
        plugin = loader.load_plugin("example_llm")
        
        # プロバイダーのインスタンスを作成
        provider = plugin.provider_class(
            api_key="test-key",
            model="test-model"
        )
        
        # generate メソッドのテスト
        result = await provider.generate("Hello")
        
        assert isinstance(result, str)
        assert "Example LLM Response" in result
        assert "test-model" in result
    
    async def test_example_llm_custom_responses(self):
        """カスタム応答のテスト"""
        loader = PluginLoader(auto_register=False)
        plugin = loader.load_plugin("example_llm")
        
        provider = plugin.provider_class(
            api_key="test-key",
            model="test-model",
            responses={"Hello": "Hi there!"}
        )
        
        result = await provider.generate("Hello")
        
        assert result == "Hi there!"


class TestGlobalPluginLoader:
    """グローバルプラグインローダーのテスト"""
    
    def test_get_plugin_loader(self):
        """get_plugin_loader のテスト"""
        loader1 = get_plugin_loader()
        loader2 = get_plugin_loader()
        
        # 同じインスタンスが返される
        assert loader1 is loader2
    
    def test_auto_load_plugins(self):
        """auto_load_plugins のテスト"""
        plugins = auto_load_plugins()
        
        assert len(plugins) > 0
        assert any(p.metadata.name == "example_llm" for p in plugins)


class TestPluginIntegration:
    """プラグイン統合テスト"""
    
    def test_plugin_with_factory(self):
        """ProviderFactoryとの統合テスト"""
        from src.core.factory import ProviderFactory
        
        # プラグインを読み込み
        loader = PluginLoader()
        loader.discover_and_register()
        
        # ファクトリーから作成できることを確認
        provider = ProviderFactory.create_llm_provider(
            "example_llm",
            {"api_key": "test-key"}
        )
        
        assert provider is not None
        assert provider.api_key == "test-key"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

