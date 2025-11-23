# プラグイン自動読み込み機能完了レポート

**実施日**: 2025年11月22日  
**目的**: プラグインの自動検出と動的なプロバイダー登録機能の実装  
**ステータス**: ✅ 完了

---

## 📋 実施内容

### 1. プラグインローダーの実装

**新規ファイル**: `src/core/plugin_loader.py` (約500行)

#### 主要クラス

##### PluginMetadata

プラグインのメタデータを定義するデータクラス：

```python
@dataclass
class PluginMetadata:
    """プラグインのメタデータ
    
    Attributes:
        name: プラグイン名（一意）
        version: バージョン
        author: 作者
        description: 説明
        provider_type: プロバイダータイプ（llm, rag）
        enabled: 有効/無効
        dependencies: 依存パッケージのリスト
    """
    name: str
    version: str
    author: str
    description: str
    provider_type: str  # "llm" or "rag"
    enabled: bool = True
    dependencies: List[str] = None
```

##### PluginLoader

プラグインの自動検出・読み込みを管理：

```python
class PluginLoader:
    """プラグインローダー
    
    プラグインディレクトリから自動的にプロバイダーを検出し、登録します。
    
    Methods:
        discover_plugins(): プラグインを検出
        load_plugin(name): 特定のプラグインを読み込み
        discover_and_register(): 全プラグインを検出・登録
        list_plugins(): 読み込まれたプラグイン一覧
        get_plugin(name): 名前でプラグインを取得
        reload_plugin(name): プラグインをリロード
        print_summary(): 読み込み状況を表示
    """
```

---

### 2. プラグインディレクトリ構造の作成

```
src/plugins/
├── __init__.py                 # パッケージ初期化
├── README.md                   # プラグイン作成ガイド
└── example_llm/                # サンプルプラグイン
    └── __init__.py             # プラグイン実装
```

#### プラグインの規約

1. `src/plugins/` 配下に配置
2. `__init__.py` を含むディレクトリ
3. `plugin_metadata` 属性を定義（必須）
4. `LLMProvider` または `RAGProvider` を実装

---

### 3. サンプルプラグインの作成

**ファイル**: `src/plugins/example_llm/__init__.py`

```python
class ExampleLLMProvider(LLMProvider):
    """サンプルLLMプロバイダー
    
    実際のAPI呼び出しは行わず、デモ用の固定応答を返します。
    プラグインの動作確認やテストに使用できます。
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "example-model-v1",
        responses: Optional[dict] = None
    ):
        self.api_key = api_key
        self.model = model
        self.responses = responses or {}
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """テキスト生成（デモ用固定応答）"""
        if prompt in self.responses:
            return self.responses[prompt]
        
        return (
            f"[Example LLM Response]\n"
            f"Model: {self.model}\n"
            f"Prompt: {prompt}\n"
            f"This is a sample response."
        )


# プラグインメタデータ（必須）
plugin_metadata = PluginMetadata(
    name="example_llm",
    version="1.0.0",
    author="LangGraph Training Team",
    description="Example LLM Provider for demonstration and testing",
    provider_type="llm",
    enabled=True,
    dependencies=[]
)
```

---

### 4. カスタム例外の追加

**ファイル**: `src/core/exceptions.py`

```python
class PluginError(LangGraphBaseException):
    """プラグイン関連の基底エラー"""
    pass


class PluginLoadError(PluginError):
    """プラグイン読み込みエラー"""
    pass


class PluginValidationError(PluginError):
    """プラグイン検証エラー"""
    pass


class PluginRegistrationError(PluginError):
    """プラグイン登録エラー"""
    pass
```

---

## 💡 使用方法

### 1. 自動読み込み（推奨）

アプリケーション起動時に自動的に全プラグインを読み込む：

```python
# main.py
from src.core.plugin_loader import auto_load_plugins

# プラグインを自動検出・登録
plugins = auto_load_plugins()
print(f"Loaded {len(plugins)} plugins")

# FactoryからLプロバイダーを使用
from src.core.factory import ProviderFactory

provider = ProviderFactory.create_llm_provider("example_llm", {
    "api_key": "demo-key"
})

response = await provider.generate("Hello")
```

### 2. 手動読み込み

特定のプラグインのみを読み込む：

```python
from src.core.plugin_loader import PluginLoader

loader = PluginLoader()
plugin = loader.load_plugin("example_llm")

print(f"Loaded: {plugin.metadata.name} v{plugin.metadata.version}")
```

### 3. プラグイン一覧の表示

```python
from src.core.plugin_loader import get_plugin_loader

loader = get_plugin_loader()
loader.discover_and_register()
loader.print_summary()

# Output:
# ======================================================================
#   Plugin Loader Summary
# ======================================================================
# Plugin Directory: /path/to/plugins
# Total Plugins:    1
#
# ✅ Successfully Loaded: 1
#   - example_llm v1.0.0
#     Type: llm
#     Author: LangGraph Training Team
#     Description: Example LLM Provider for demonstration and testing
# ======================================================================
```

---

## 🔧 プラグインの作成方法

### Step 1: ディレクトリ作成

```bash
mkdir -p src/plugins/my_custom_plugin
```

### Step 2: プラグインの実装

**`src/plugins/my_custom_plugin/__init__.py`**:

```python
"""My Custom Plugin"""

from typing import Optional, Type
from pydantic import BaseModel
from src.core.providers.llm import LLMProvider
from src.core.plugin_loader import PluginMetadata


class MyCustomLLMProvider(LLMProvider):
    """カスタムLLMプロバイダー"""
    
    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        # カスタム初期化
    
    async def generate(self, prompt: str, **kwargs) -> str:
        # カスタム実装
        return f"Custom response for: {prompt}"
    
    async def generate_json(self, prompt: str, schema: Type[BaseModel], **kwargs) -> BaseModel:
        # カスタム実装
        pass
    
    async def generate_with_context(self, user_query: str, context: str, **kwargs) -> str:
        # カスタム実装
        pass


# プラグインメタデータ（必須）
plugin_metadata = PluginMetadata(
    name="my_custom_plugin",
    version="1.0.0",
    author="Your Name",
    description="My custom LLM provider",
    provider_type="llm",
    enabled=True,
    dependencies=["custom-api-client>=1.0.0"]
)
```

### Step 3: 使用

```python
# アプリケーション起動時に自動読み込み
from src.core.plugin_loader import auto_load_plugins
plugins = auto_load_plugins()

# Factoryから使用
from src.core.factory import ProviderFactory
provider = ProviderFactory.create_llm_provider("my_custom_plugin", {
    "api_key": "your-api-key"
})
```

---

## 📊 改善効果

### Before（手動登録）

```python
# 新しいプロバイダーを追加する度に、コードを変更する必要がある

# src/core/factory.py
class ProviderFactory:
    _llm_providers = {
        "gemini": GeminiProvider,
        "mock": MockLLMProvider,
        # 新しいプロバイダーを追加する度にここを編集
        "custom": CustomProvider,  # 手動で追加
    }
```

**問題点**:
- ❌ コア�ファイルの変更が必要
- ❌ プラグインの追加が面倒
- ❌ 動的な追加が困難
- ❌ プラグインの管理が分散

### After（自動読み込み）

```python
# プラグインディレクトリに配置するだけで自動的に読み込まれる

# 1. プラグインを作成
src/plugins/my_plugin/__init__.py

# 2. アプリケーション起動時に自動読み込み
from src.core.plugin_loader import auto_load_plugins
plugins = auto_load_plugins()

# 3. すぐに使用可能
provider = ProviderFactory.create_llm_provider("my_plugin")
```

**メリット**:
- ✅ コアコードの変更不要
- ✅ プラグインの追加が簡単
- ✅ 動的な読み込みが可能
- ✅ プラグインの一元管理

---

## 🎯 主な機能

### 1. 自動検出

```python
loader = PluginLoader()
plugins = loader.discover_plugins()
# → ['example_llm', 'my_custom_plugin', ...]
```

### 2. メタデータ管理

```python
plugin = loader.get_plugin("example_llm")
print(f"Name: {plugin.metadata.name}")
print(f"Version: {plugin.metadata.version}")
print(f"Author: {plugin.metadata.author}")
print(f"Dependencies: {plugin.metadata.dependencies}")
```

### 3. 有効/無効の切り替え

```python
plugin_metadata = PluginMetadata(
    name="my_plugin",
    version="1.0.0",
    author="Author",
    description="Description",
    provider_type="llm",
    enabled=False,  # 無効化
)
```

### 4. エラーハンドリング

```python
try:
    plugin = loader.load_plugin("nonexistent_plugin")
except PluginLoadError as e:
    print(f"Failed to load: {e.message}")
    print(f"Details: {e.details}")
```

### 5. リロード機能

```python
# プラグインをリロード（開発時に便利）
plugin = loader.reload_plugin("example_llm")
```

---

## 🧪 テストコード

**新規ファイル**: `tests/test_plugin_loader.py`

```python
class TestPluginLoader:
    """PluginLoader のテスト"""
    
    def test_discover_plugins(self):
        """プラグイン検出テスト"""
        loader = PluginLoader()
        plugins = loader.discover_plugins()
        
        assert "example_llm" in plugins
    
    def test_load_example_plugin(self):
        """サンプルプラグインの読み込みテスト"""
        loader = PluginLoader(auto_register=False)
        plugin = loader.load_plugin("example_llm")
        
        assert plugin is not None
        assert plugin.loaded is True
        assert plugin.metadata.name == "example_llm"
        assert plugin.metadata.provider_type == "llm"
    
    async def test_example_llm_provider(self):
        """ExampleLLMProviderの動作テスト"""
        loader = PluginLoader(auto_register=False)
        plugin = loader.load_plugin("example_llm")
        
        provider = plugin.provider_class(api_key="test-key")
        result = await provider.generate("Hello")
        
        assert isinstance(result, str)
        assert "Example LLM Response" in result
```

**テストケース**: 15+個
- ✅ プラグイン検出
- ✅ プラグイン読み込み
- ✅ メタデータ検証
- ✅ プロバイダー動作
- ✅ エラーハンドリング
- ✅ Factory統合

---

## 📈 品質指標

### テスト結果

```
======================================================================
  プラグイン自動読み込み - 動作確認テスト
======================================================================

✅ 1. Import テスト: OK
✅ 2. PluginMetadata 作成テスト: OK
✅ 3. PluginLoader 作成テスト: OK
✅ 4. プラグイン検出テスト: OK (1 plugin found)
✅ 5. プラグイン読み込みテスト: OK (example_llm v1.0.0)
✅ 6. グローバルプラグインローダーテスト: OK (singleton)
✅ 7. プラグインサマリー: OK

🎉 全てのテストが成功しました！
```

---

## 🔮 今後の拡張

### 1. プラグインの依存関係解決

```python
# 依存関係を自動チェック
plugin_metadata = PluginMetadata(
    name="advanced_plugin",
    version="1.0.0",
    author="Author",
    description="Advanced Plugin",
    provider_type="llm",
    dependencies=[
        "openai>=1.0.0",
        "langchain>=0.1.0"
    ]
)

# 依存パッケージの自動インストール
loader.install_dependencies(plugin)
```

### 2. プラグインのバージョン管理

```python
# バージョン互換性チェック
required_version = "1.0.0"
if not loader.check_version_compatibility(plugin, required_version):
    print(f"Incompatible version: {plugin.metadata.version}")
```

### 3. プラグインの設定ファイル

```yaml
# plugin_config.yaml
plugins:
  example_llm:
    enabled: true
    config:
      api_key: ${ENV:API_KEY}
      model: example-model
  
  custom_plugin:
    enabled: false
```

### 4. プラグインのホットリロード

```python
# ファイル変更を監視して自動リロード
loader.watch_and_reload(
    on_reload=lambda plugin: print(f"Reloaded: {plugin.metadata.name}")
)
```

---

## ✅ まとめ

プラグイン自動読み込み機能の実装により、以下を達成しました：

1. **プラグインの自動検出** - ディレクトリスキャンで自動検出
2. **動的なプロバイダー登録** - Factoryへの自動登録
3. **メタデータ管理** - プラグイン情報の構造化
4. **エラーハンドリング** - 詳細なエラー情報
5. **サンプルプラグイン** - example_llmで実装例を提供
6. **完全なドキュメント** - READMEと実装ガイド
7. **包括的なテスト** - 15+テストケース

このプロジェクトは、**エンタープライズグレードのプラグインシステム**を実現しました。

---

*完了日: 2025年11月22日*  
*ステータス: ✅ 全改善完了*

