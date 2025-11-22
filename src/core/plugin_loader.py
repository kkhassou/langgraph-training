"""Plugin Loader - プラグインの自動読み込み機能

このモジュールは、プラグインディレクトリから自動的にプロバイダーを検出し、
ProviderFactoryに登録する機能を提供します。

プラグインの規約:
    1. src/plugins/ 配下に配置
    2. LLMProvider または RAGProvider を実装
    3. plugin_metadata 属性でメタデータを定義
    4. __init__.py で公開

Example:
    >>> from src.core.plugin_loader import PluginLoader
    >>> 
    >>> # プラグインを自動検出・登録
    >>> loader = PluginLoader()
    >>> loaded_plugins = loader.discover_and_register()
    >>> print(f"Loaded {len(loaded_plugins)} plugins")
    >>> 
    >>> # 特定のプラグインを読み込み
    >>> loader.load_plugin("custom_llm")
"""

import os
import sys
import importlib
import inspect
import logging
from typing import List, Dict, Any, Type, Optional, Callable
from pathlib import Path
from dataclasses import dataclass

from src.core.providers.llm import LLMProvider
from src.core.providers.rag import RAGProvider
from src.core.factory import ProviderFactory
from src.core.exceptions import PluginLoadError, PluginValidationError

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """プラグインのメタデータ
    
    Attributes:
        name: プラグイン名（一意）
        version: バージョン（セマンティックバージョニング推奨）
        author: 作者
        description: 説明
        provider_type: プロバイダータイプ（llm, rag）
        enabled: 有効/無効
        dependencies: 依存パッケージのリスト
    
    Example:
        >>> metadata = PluginMetadata(
        ...     name="custom_llm",
        ...     version="1.0.0",
        ...     author="John Doe",
        ...     description="Custom LLM Provider",
        ...     provider_type="llm",
        ...     enabled=True,
        ...     dependencies=["openai>=1.0.0"]
        ... )
    """
    name: str
    version: str
    author: str
    description: str
    provider_type: str  # "llm" or "rag"
    enabled: bool = True
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        
        # provider_typeの検証
        if self.provider_type not in ["llm", "rag"]:
            raise ValueError(f"Invalid provider_type: {self.provider_type}. Must be 'llm' or 'rag'")


@dataclass
class LoadedPlugin:
    """読み込まれたプラグイン情報
    
    Attributes:
        metadata: プラグインのメタデータ
        provider_class: プロバイダークラス
        module_path: モジュールパス
        loaded: 読み込み成功フラグ
        error: エラーメッセージ（読み込み失敗時）
    """
    metadata: PluginMetadata
    provider_class: Type
    module_path: str
    loaded: bool = True
    error: Optional[str] = None


class PluginLoader:
    """プラグインローダー
    
    プラグインディレクトリから自動的にプロバイダーを検出し、登録します。
    
    Attributes:
        plugin_dir: プラグインディレクトリのパス
        loaded_plugins: 読み込まれたプラグインのリスト
        auto_register: 自動登録フラグ
    
    Example:
        >>> loader = PluginLoader()
        >>> plugins = loader.discover_and_register()
        >>> print(f"Loaded: {[p.metadata.name for p in plugins]}")
        >>> 
        >>> # プラグイン一覧を表示
        >>> loader.list_plugins()
    """
    
    def __init__(
        self,
        plugin_dir: Optional[str] = None,
        auto_register: bool = True
    ):
        """
        Args:
            plugin_dir: プラグインディレクトリのパス（デフォルト: src/plugins）
            auto_register: 検出時に自動的にFactoryに登録するか
        """
        if plugin_dir is None:
            # デフォルトのプラグインディレクトリ
            project_root = Path(__file__).parent.parent.parent
            plugin_dir = project_root / "src" / "plugins"
        
        self.plugin_dir = Path(plugin_dir)
        self.auto_register = auto_register
        self.loaded_plugins: List[LoadedPlugin] = []
        
        logger.info(f"PluginLoader initialized with directory: {self.plugin_dir}")
    
    def discover_plugins(self) -> List[str]:
        """プラグインディレクトリをスキャンしてプラグインを検出
        
        Returns:
            検出されたプラグインモジュール名のリスト
        
        Example:
            >>> loader = PluginLoader()
            >>> plugins = loader.discover_plugins()
            >>> print(plugins)  # ['custom_llm', 'custom_rag']
        """
        if not self.plugin_dir.exists():
            logger.warning(f"Plugin directory does not exist: {self.plugin_dir}")
            return []
        
        plugins = []
        
        # プラグインディレクトリ配下のサブディレクトリを検索
        for item in self.plugin_dir.iterdir():
            if not item.is_dir():
                continue
            
            # __pycache__ などを除外
            if item.name.startswith('_') and item.name != '__init__.py':
                continue
            
            # __init__.py が存在するディレクトリのみ
            init_file = item / "__init__.py"
            if init_file.exists():
                plugins.append(item.name)
                logger.debug(f"Discovered plugin: {item.name}")
        
        logger.info(f"Discovered {len(plugins)} plugins: {plugins}")
        return plugins
    
    def load_plugin(self, plugin_name: str) -> Optional[LoadedPlugin]:
        """特定のプラグインを読み込む
        
        Args:
            plugin_name: プラグイン名（ディレクトリ名）
        
        Returns:
            LoadedPlugin: 読み込まれたプラグイン情報
        
        Raises:
            PluginLoadError: プラグインの読み込みに失敗した場合
            PluginValidationError: プラグインの検証に失敗した場合
        
        Example:
            >>> loader = PluginLoader()
            >>> plugin = loader.load_plugin("custom_llm")
            >>> print(plugin.metadata.name)
        """
        try:
            # モジュールをインポート
            module_path = f"src.plugins.{plugin_name}"
            logger.info(f"Loading plugin: {plugin_name} from {module_path}")
            
            # sys.pathにプラグインディレクトリを追加
            if str(self.plugin_dir.parent.parent) not in sys.path:
                sys.path.insert(0, str(self.plugin_dir.parent.parent))
            
            module = importlib.import_module(module_path)
            
            # メタデータの取得
            if not hasattr(module, 'plugin_metadata'):
                raise PluginValidationError(
                    f"Plugin '{plugin_name}' does not have 'plugin_metadata' attribute",
                    details={"plugin": plugin_name, "module_path": module_path}
                )
            
            metadata = module.plugin_metadata
            
            # メタデータの検証
            if not isinstance(metadata, PluginMetadata):
                raise PluginValidationError(
                    f"Plugin '{plugin_name}' metadata is not PluginMetadata instance",
                    details={"plugin": plugin_name, "metadata_type": type(metadata)}
                )
            
            # プラグインが無効な場合はスキップ
            if not metadata.enabled:
                logger.info(f"Plugin '{plugin_name}' is disabled, skipping")
                return None
            
            # プロバイダークラスの検出
            provider_class = self._find_provider_class(module, metadata.provider_type)
            
            if provider_class is None:
                raise PluginValidationError(
                    f"No valid provider class found in plugin '{plugin_name}'",
                    details={"plugin": plugin_name, "expected_type": metadata.provider_type}
                )
            
            # LoadedPluginを作成
            loaded_plugin = LoadedPlugin(
                metadata=metadata,
                provider_class=provider_class,
                module_path=module_path,
                loaded=True
            )
            
            # 自動登録
            if self.auto_register:
                self._register_plugin(loaded_plugin)
            
            self.loaded_plugins.append(loaded_plugin)
            logger.info(f"Successfully loaded plugin: {plugin_name}")
            
            return loaded_plugin
            
        except Exception as e:
            error_msg = f"Failed to load plugin '{plugin_name}': {e}"
            logger.error(error_msg)
            
            # エラー情報を記録
            loaded_plugin = LoadedPlugin(
                metadata=PluginMetadata(
                    name=plugin_name,
                    version="unknown",
                    author="unknown",
                    description="Failed to load",
                    provider_type="unknown"
                ),
                provider_class=None,
                module_path=f"src.plugins.{plugin_name}",
                loaded=False,
                error=str(e)
            )
            self.loaded_plugins.append(loaded_plugin)
            
            raise PluginLoadError(
                error_msg,
                original_error=e,
                details={"plugin": plugin_name}
            )
    
    def _find_provider_class(
        self,
        module,
        provider_type: str
    ) -> Optional[Type]:
        """モジュールからプロバイダークラスを検出
        
        Args:
            module: インポートされたモジュール
            provider_type: プロバイダータイプ（llm, rag）
        
        Returns:
            検出されたプロバイダークラス、見つからない場合はNone
        """
        base_class = LLMProvider if provider_type == "llm" else RAGProvider
        
        for name, obj in inspect.getmembers(module):
            # クラスかどうか確認
            if not inspect.isclass(obj):
                continue
            
            # 基底クラスを継承しているか確認
            if issubclass(obj, base_class) and obj is not base_class:
                logger.debug(f"Found provider class: {name}")
                return obj
        
        return None
    
    def _register_plugin(self, plugin: LoadedPlugin):
        """プラグインをProviderFactoryに登録
        
        Args:
            plugin: 登録するプラグイン情報
        """
        try:
            if plugin.metadata.provider_type == "llm":
                ProviderFactory.register_llm_provider(
                    plugin.metadata.name,
                    plugin.provider_class
                )
                logger.info(f"Registered LLM provider: {plugin.metadata.name}")
            
            elif plugin.metadata.provider_type == "rag":
                ProviderFactory.register_rag_provider(
                    plugin.metadata.name,
                    plugin.provider_class
                )
                logger.info(f"Registered RAG provider: {plugin.metadata.name}")
            
        except Exception as e:
            logger.error(f"Failed to register plugin '{plugin.metadata.name}': {e}")
            raise
    
    def discover_and_register(self) -> List[LoadedPlugin]:
        """プラグインを検出し、自動的に登録
        
        Returns:
            読み込まれたプラグインのリスト
        
        Example:
            >>> loader = PluginLoader()
            >>> plugins = loader.discover_and_register()
            >>> print(f"Loaded {len(plugins)} plugins")
            >>> for plugin in plugins:
            ...     print(f"  - {plugin.metadata.name} v{plugin.metadata.version}")
        """
        plugin_names = self.discover_plugins()
        
        successfully_loaded = []
        
        for plugin_name in plugin_names:
            try:
                plugin = self.load_plugin(plugin_name)
                if plugin is not None:
                    successfully_loaded.append(plugin)
            except Exception as e:
                logger.error(f"Skipping plugin '{plugin_name}' due to error: {e}")
                continue
        
        logger.info(
            f"Successfully loaded {len(successfully_loaded)}/{len(plugin_names)} plugins"
        )
        
        return successfully_loaded
    
    def list_plugins(self, include_failed: bool = False) -> List[LoadedPlugin]:
        """読み込まれたプラグインの一覧を取得
        
        Args:
            include_failed: 失敗したプラグインも含めるか
        
        Returns:
            プラグインのリスト
        
        Example:
            >>> loader = PluginLoader()
            >>> loader.discover_and_register()
            >>> plugins = loader.list_plugins()
            >>> for p in plugins:
            ...     print(f"{p.metadata.name}: {p.metadata.description}")
        """
        if include_failed:
            return self.loaded_plugins
        else:
            return [p for p in self.loaded_plugins if p.loaded]
    
    def get_plugin(self, name: str) -> Optional[LoadedPlugin]:
        """名前でプラグインを取得
        
        Args:
            name: プラグイン名
        
        Returns:
            プラグイン情報、見つからない場合はNone
        """
        for plugin in self.loaded_plugins:
            if plugin.metadata.name == name:
                return plugin
        return None
    
    def reload_plugin(self, plugin_name: str) -> Optional[LoadedPlugin]:
        """プラグインをリロード
        
        Args:
            plugin_name: プラグイン名
        
        Returns:
            リロードされたプラグイン情報
        """
        # 既存のプラグインを削除
        self.loaded_plugins = [
            p for p in self.loaded_plugins
            if p.metadata.name != plugin_name
        ]
        
        # モジュールをリロード
        module_path = f"src.plugins.{plugin_name}"
        if module_path in sys.modules:
            importlib.reload(sys.modules[module_path])
        
        # 再読み込み
        return self.load_plugin(plugin_name)
    
    def print_summary(self):
        """プラグインの読み込み状況を表示"""
        print("=" * 70)
        print("  Plugin Loader Summary")
        print("=" * 70)
        print(f"Plugin Directory: {self.plugin_dir}")
        print(f"Total Plugins:    {len(self.loaded_plugins)}")
        print()
        
        successful = [p for p in self.loaded_plugins if p.loaded]
        failed = [p for p in self.loaded_plugins if not p.loaded]
        
        print(f"✅ Successfully Loaded: {len(successful)}")
        for plugin in successful:
            print(f"  - {plugin.metadata.name} v{plugin.metadata.version}")
            print(f"    Type: {plugin.metadata.provider_type}")
            print(f"    Author: {plugin.metadata.author}")
            print(f"    Description: {plugin.metadata.description}")
        
        if failed:
            print()
            print(f"❌ Failed to Load: {len(failed)}")
            for plugin in failed:
                print(f"  - {plugin.metadata.name}")
                print(f"    Error: {plugin.error}")
        
        print("=" * 70)


# ============================================================================
# Global Plugin Loader Instance
# ============================================================================

_plugin_loader: Optional[PluginLoader] = None


def get_plugin_loader() -> PluginLoader:
    """グローバルプラグインローダーインスタンスを取得
    
    Returns:
        PluginLoader: グローバルインスタンス
    
    Example:
        >>> loader = get_plugin_loader()
        >>> plugins = loader.discover_and_register()
    """
    global _plugin_loader
    if _plugin_loader is None:
        _plugin_loader = PluginLoader()
    return _plugin_loader


def auto_load_plugins() -> List[LoadedPlugin]:
    """プラグインを自動的に検出・登録
    
    この関数はアプリケーション起動時に呼び出すことを推奨します。
    
    Returns:
        読み込まれたプラグインのリスト
    
    Example:
        >>> # main.py
        >>> from src.core.plugin_loader import auto_load_plugins
        >>> 
        >>> plugins = auto_load_plugins()
        >>> print(f"Loaded {len(plugins)} plugins")
    """
    loader = get_plugin_loader()
    return loader.discover_and_register()


if __name__ == "__main__":
    # テスト実行
    loader = PluginLoader()
    plugins = loader.discover_and_register()
    loader.print_summary()

