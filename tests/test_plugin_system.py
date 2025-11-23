"""プラグインシステムの拡張機能テスト

このモジュールは、プラグインシステムの新機能をテストします：
- plugin.jsonマニフェストのサポート
- プラグインレジストリ
- プラグイン検証機能
- 依存関係チェック
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

from src.core.plugin_loader import (
    PluginMetadata,
    PluginLoader,
    PluginRegistry,
    LoadedPlugin,
    get_plugin_registry
)
from src.core.providers.llm import LLMProvider
from src.core.exceptions import PluginLoadError, PluginValidationError


class TestPluginMetadata:
    """PluginMetadataクラスのテスト"""
    
    def test_metadata_creation(self):
        """基本的なメタデータ作成のテスト"""
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
    
    def test_metadata_with_dependencies(self):
        """依存関係を含むメタデータのテスト"""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            author="Test Author",
            description="Test Description",
            provider_type="llm",
            dependencies=["openai>=1.0.0", "requests"]
        )
        
        assert len(metadata.dependencies) == 2
        assert "openai>=1.0.0" in metadata.dependencies
    
    def test_invalid_provider_type(self):
        """不正なプロバイダータイプのテスト"""
        with pytest.raises(ValueError, match="Invalid provider_type"):
            PluginMetadata(
                name="test_plugin",
                version="1.0.0",
                author="Test Author",
                description="Test Description",
                provider_type="invalid"
            )
    
    def test_metadata_from_json_file(self):
        """plugin.jsonからのメタデータ読み込みテスト"""
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json_data = {
                "name": "test_plugin",
                "version": "1.0.0",
                "author": "Test Author",
                "description": "Test Description",
                "provider_type": "llm",
                "enabled": True,
                "entry_point": "provider",
                "dependencies": ["openai>=1.0.0"],
                "config": {"key": "value"}
            }
            json.dump(json_data, f)
            temp_path = Path(f.name)
        
        try:
            # JSONファイルから読み込み
            metadata = PluginMetadata.from_json_file(temp_path)
            
            assert metadata.name == "test_plugin"
            assert metadata.version == "1.0.0"
            assert metadata.entry_point == "provider"
            assert metadata.config == {"key": "value"}
        finally:
            # 一時ファイルを削除
            temp_path.unlink()
    
    def test_metadata_to_dict(self):
        """メタデータの辞書変換テスト"""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            author="Test Author",
            description="Test Description",
            provider_type="llm"
        )
        
        data = metadata.to_dict()
        
        assert isinstance(data, dict)
        assert data["name"] == "test_plugin"
        assert data["version"] == "1.0.0"
        assert "dependencies" in data
        assert "config" in data


class TestPluginRegistry:
    """PluginRegistryクラスのテスト"""
    
    def setup_method(self):
        """各テストの前にレジストリをクリア"""
        registry = PluginRegistry.get_instance()
        registry.clear()
    
    def test_singleton_pattern(self):
        """シングルトンパターンのテスト"""
        registry1 = PluginRegistry.get_instance()
        registry2 = PluginRegistry.get_instance()
        
        assert registry1 is registry2
    
    def test_register_plugin(self):
        """プラグイン登録のテスト"""
        registry = PluginRegistry.get_instance()
        
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            author="Test",
            description="Test",
            provider_type="llm"
        )
        
        plugin = LoadedPlugin(
            metadata=metadata,
            provider_class=LLMProvider,
            module_path="test.plugin",
            loaded=True
        )
        
        registry.register(plugin)
        
        # 登録されたプラグインを取得
        retrieved = registry.get_plugin("test_plugin")
        assert retrieved is not None
        assert retrieved.metadata.name == "test_plugin"
    
    def test_get_plugins_by_type(self):
        """タイプ別プラグイン取得のテスト"""
        registry = PluginRegistry.get_instance()
        
        # LLMプラグインを登録
        llm_metadata = PluginMetadata(
            name="llm_plugin",
            version="1.0.0",
            author="Test",
            description="Test",
            provider_type="llm"
        )
        llm_plugin = LoadedPlugin(
            metadata=llm_metadata,
            provider_class=LLMProvider,
            module_path="test.llm",
            loaded=True
        )
        registry.register(llm_plugin)
        
        # RAGプラグインを登録
        from src.core.providers.rag import RAGProvider
        rag_metadata = PluginMetadata(
            name="rag_plugin",
            version="1.0.0",
            author="Test",
            description="Test",
            provider_type="rag"
        )
        rag_plugin = LoadedPlugin(
            metadata=rag_metadata,
            provider_class=RAGProvider,
            module_path="test.rag",
            loaded=True
        )
        registry.register(rag_plugin)
        
        # タイプ別に取得
        llm_plugins = registry.get_plugins_by_type("llm")
        rag_plugins = registry.get_plugins_by_type("rag")
        
        assert len(llm_plugins) == 1
        assert len(rag_plugins) == 1
        assert llm_plugins[0].metadata.name == "llm_plugin"
        assert rag_plugins[0].metadata.name == "rag_plugin"
    
    def test_enable_disable_plugin(self):
        """プラグインの有効化/無効化のテスト"""
        registry = PluginRegistry.get_instance()
        
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            author="Test",
            description="Test",
            provider_type="llm"
        )
        plugin = LoadedPlugin(
            metadata=metadata,
            provider_class=LLMProvider,
            module_path="test.plugin",
            loaded=True
        )
        
        registry.register(plugin)
        
        # 初期状態は有効
        assert plugin.metadata.enabled is True
        
        # 無効化
        registry.disable_plugin("test_plugin")
        assert plugin.metadata.enabled is False
        
        # 有効化
        registry.enable_plugin("test_plugin")
        assert plugin.metadata.enabled is True
    
    def test_get_statistics(self):
        """統計情報取得のテスト"""
        registry = PluginRegistry.get_instance()
        
        # 複数のプラグインを登録
        for i in range(3):
            metadata = PluginMetadata(
                name=f"plugin_{i}",
                version="1.0.0",
                author="Test",
                description="Test",
                provider_type="llm" if i < 2 else "rag"
            )
            plugin = LoadedPlugin(
                metadata=metadata,
                provider_class=LLMProvider,
                module_path=f"test.plugin_{i}",
                loaded=True
            )
            registry.register(plugin)
        
        stats = registry.get_statistics()
        
        assert stats["total"] == 3
        assert stats["loaded"] == 3
        assert stats["enabled"] == 3
        assert stats["by_type"]["llm"] == 2
        assert stats["by_type"]["rag"] == 1
    
    def test_export_metadata(self):
        """メタデータエクスポートのテスト"""
        registry = PluginRegistry.get_instance()
        
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            author="Test",
            description="Test",
            provider_type="llm"
        )
        plugin = LoadedPlugin(
            metadata=metadata,
            provider_class=LLMProvider,
            module_path="test.plugin",
            loaded=True
        )
        
        registry.register(plugin)
        
        # エクスポート
        exported = registry.export_metadata()
        
        assert len(exported) == 1
        assert exported[0]["name"] == "test_plugin"
        assert exported[0]["version"] == "1.0.0"


class TestPluginLoader:
    """PluginLoaderの拡張機能テスト"""
    
    def test_discover_plugins_with_json(self):
        """plugin.jsonを持つプラグインの検出テスト"""
        # 一時ディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # プラグインディレクトリを作成
            plugin_dir = temp_path / "test_plugin"
            plugin_dir.mkdir()
            
            # plugin.jsonを作成
            plugin_json = plugin_dir / "plugin.json"
            with open(plugin_json, 'w') as f:
                json.dump({
                    "name": "test_plugin",
                    "version": "1.0.0",
                    "author": "Test",
                    "description": "Test",
                    "provider_type": "llm"
                }, f)
            
            # PluginLoaderで検出
            loader = PluginLoader(plugin_dir=str(temp_path))
            plugins = loader.discover_plugins()
            
            assert "test_plugin" in plugins
    
    def test_load_metadata_from_json(self):
        """plugin.jsonからのメタデータ読み込みテスト"""
        # 一時ディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # プラグインディレクトリを作成
            plugin_dir = temp_path / "test_plugin"
            plugin_dir.mkdir()
            
            # plugin.jsonを作成
            plugin_json = plugin_dir / "plugin.json"
            with open(plugin_json, 'w') as f:
                json.dump({
                    "name": "test_plugin",
                    "version": "1.0.0",
                    "author": "Test Author",
                    "description": "Test Description",
                    "provider_type": "llm",
                    "entry_point": "custom_provider"
                }, f)
            
            # PluginLoaderで読み込み
            loader = PluginLoader(plugin_dir=str(temp_path))
            metadata = loader._load_plugin_metadata("test_plugin", plugin_dir)
            
            assert metadata.name == "test_plugin"
            assert metadata.entry_point == "custom_provider"
    
    def test_validate_dependencies(self):
        """依存関係検証のテスト"""
        loader = PluginLoader()
        
        # 存在するパッケージ
        metadata1 = PluginMetadata(
            name="test1",
            version="1.0.0",
            author="Test",
            description="Test",
            provider_type="llm",
            dependencies=["pathlib", "json"]  # 標準ライブラリ
        )
        
        # エラーにならないことを確認（警告のみ）
        try:
            loader._validate_dependencies(metadata1)
        except Exception as e:
            pytest.fail(f"Validation should not raise error: {e}")
        
        # 存在しないパッケージ（警告のみ、エラーにはならない）
        metadata2 = PluginMetadata(
            name="test2",
            version="1.0.0",
            author="Test",
            description="Test",
            provider_type="llm",
            dependencies=["nonexistent_package_xyz"]
        )
        
        # 警告は出るがエラーにはならない
        try:
            loader._validate_dependencies(metadata2)
        except Exception as e:
            pytest.fail(f"Validation should not raise error: {e}")


class TestPluginIntegration:
    """プラグインシステムの統合テスト"""
    
    def setup_method(self):
        """各テストの前にレジストリをクリア"""
        registry = PluginRegistry.get_instance()
        registry.clear()
    
    def test_loader_and_registry_integration(self):
        """ローダーとレジストリの統合テスト"""
        registry = PluginRegistry.get_instance()
        
        # 初期状態: レジストリは空
        assert len(registry.get_all_plugins()) == 0
        
        # 注意: 実際のプラグインロードはテスト環境では困難なため、
        # ここではレジストリの動作のみをテストします


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

