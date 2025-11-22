# DI コンテナ実装完了レポート

**実施日**: 2025年11月22日  
**目的**: dependency-injectorライブラリを使用した依存性注入コンテナの導入  
**ステータス**: ✅ 完了

---

## 📋 実施内容

### 1. dependency-injectorライブラリの導入

**追加した依存関係**: `requirements.txt`

```txt
# Dependency Injection
dependency-injector>=4.41.0
```

**インストール方法**:
```bash
pip install dependency-injector>=4.41.0
```

---

### 2. DIコンテナの実装

**新規ファイル**: `src/core/containers.py` (約300行)

#### コンテナの構造

```python
class Container(containers.DeclarativeContainer):
    """依存性注入コンテナ
    
    全てのプロバイダー、サービス、ノード、ワークフローの依存性を管理
    """
    
    # 設定管理
    config = providers.Configuration()
    
    # Provider Layer
    gemini_provider = providers.Singleton(GeminiProvider, ...)
    mock_llm_provider = providers.Singleton(MockLLMProvider, ...)
    llm_provider = providers.Selector(...)  # 動的切り替え
    
    # Node Layer
    llm_node = providers.Factory(...)
    todo_advisor_node = providers.Factory(...)
    
    # Workflow Layer
    chat_workflow = providers.Factory(...)
    rag_query_workflow = providers.Factory(...)
    
    # Service Layer
    rag_service = providers.Factory(...)
```

#### 主な機能

1. **設定ベースの構成**
   ```python
   container.config.from_dict({
       'llm_provider_type': 'gemini',
       'gemini': {
           'api_key': 'your-api-key',
           'model': 'gemini-2.0-flash-exp'
       }
   })
   ```

2. **動的プロバイダー切り替え**
   ```python
   # Geminiプロバイダー
   container.config.llm_provider_type.from_value('gemini')
   provider1 = container.llm_provider()
   
   # Mockプロバイダーに切り替え
   container.config.llm_provider_type.from_value('mock')
   provider2 = container.llm_provider()
   ```

3. **シングルトンパターン**
   ```python
   # 同じインスタンスが返される
   provider1 = container.gemini_provider()
   provider2 = container.gemini_provider()
   assert provider1 is provider2  # True
   ```

4. **自動依存性注入**
   ```python
   # ワークフローを作成（プロバイダーは自動注入）
   workflow = container.chat_workflow()
   # workflow.llm_node.providerは自動的に設定される
   ```

---

### 3. 便利関数の提供

#### グローバルコンテナアクセス

```python
from src.core.containers import get_container

container = get_container()
provider = container.llm_provider()
```

#### 型別の便利関数

```python
from src.core.containers import (
    get_llm_provider,
    get_rag_provider,
    get_chat_workflow,
    get_rag_query_workflow
)

# LLMプロバイダーを取得
provider = get_llm_provider()

# ワークフローを取得（依存性は自動注入）
workflow = get_chat_workflow()
```

---

### 4. 後方互換性の維持

**既存のProviderFactoryとの統合**: `src/core/factory.py`

```python
# DIコンテナを使用するかどうかのフラグ
_USE_DI_CONTAINER = True

@classmethod
def get_default_llm_provider(cls) -> LLMProvider:
    """デフォルトのLLMプロバイダーを取得"""
    if _USE_DI_CONTAINER:
        try:
            from src.core.containers import get_llm_provider
            return get_llm_provider()
        except Exception as e:
            # フォールバック: 直接作成
            logger.warning(f"Falling back to direct creation: {e}")
    
    return cls.create_llm_provider(provider_type="gemini")
```

**メリット**:
- ✅ 既存のコードは変更不要
- ✅ DIコンテナがインストールされていない場合でも動作
- ✅ 段階的な移行が可能

---

## 🎯 DIコンテナのメリット

### Before（DIコンテナなし）

```python
# 手動で依存性を管理
from src.core.factory import ProviderFactory
from src.workflows.atomic.chat import ChatWorkflow

# プロバイダーを作成
provider = ProviderFactory.create_llm_provider("gemini", config={
    "api_key": "xxx",
    "model": "gemini-2.0-flash-exp"
})

# ワークフローに手動で注入
workflow = ChatWorkflow(llm_provider=provider)
```

**問題点**:
- ❌ 依存性の管理が分散
- ❌ 設定の一元管理が困難
- ❌ テスト時の切り替えが面倒
- ❌ シングルトンの管理が手動

### After（DIコンテナあり）

```python
# DIコンテナで一元管理
from src.core.containers import get_container

container = get_container()

# 設定を一度だけ
container.config.from_dict({
    'llm_provider_type': 'gemini',
    'gemini': {
        'api_key': 'xxx',
        'model': 'gemini-2.0-flash-exp'
    }
})

# ワークフローを取得（依存性は自動注入）
workflow = container.chat_workflow()
```

**メリット**:
- ✅ 依存性が一元管理される
- ✅ 設定が統一される
- ✅ テスト時の切り替えが簡単
- ✅ シングルトンが自動管理

---

## 💡 使用例

### 例1: 基本的な使用

```python
from src.core.containers import get_llm_provider

# デフォルト設定でプロバイダーを取得
provider = get_llm_provider()
response = await provider.generate("Hello, AI!")
```

### 例2: カスタム設定

```python
from src.core.containers import Container

# カスタムコンテナを作成
container = Container()
container.config.from_dict({
    'llm_provider_type': 'gemini',
    'gemini': {
        'api_key': 'custom-key',
        'model': 'gemini-pro'
    }
})

# カスタム設定のプロバイダーを取得
provider = container.llm_provider()
```

### 例3: テスト時のモック使用

```python
from src.core.containers import Container

# テスト用コンテナ
container = Container()
container.config.from_dict({
    'llm_provider_type': 'mock',
    'mock': {
        'responses': {
            'Hello': 'Hi there!',
            'How are you?': 'I am great!'
        }
    }
})

# モックプロバイダーを使用したワークフロー
workflow = container.chat_workflow()
result = await workflow.run(ChatInput(message="Hello"))
# result.response == 'Hi there!'
```

### 例4: プロバイダーの動的切り替え

```python
from src.core.containers import get_container

container = get_container()

# 開発環境: Mockプロバイダー
if ENV == 'development':
    container.config.llm_provider_type.from_value('mock')

# 本番環境: Geminiプロバイダー
elif ENV == 'production':
    container.config.llm_provider_type.from_value('gemini')

provider = container.llm_provider()
```

### 例5: ワークフロー全体の構成

```python
from src.core.containers import get_container

# コンテナを取得
container = get_container()

# 全ての設定を一度に
container.config.from_dict({
    'llm_provider_type': 'gemini',
    'rag_provider_type': 'simple',
    'gemini': {
        'api_key': 'xxx',
        'model': 'gemini-2.0-flash-exp'
    }
})

# 全てのワークフローが同じ設定を使用
chat_workflow = container.chat_workflow()
rag_workflow = container.rag_query_workflow()

# 全てのノードも同じ設定を使用
llm_node = container.llm_node()
todo_advisor = container.todo_advisor_node()
```

---

## 📊 改善効果

### 依存性管理の改善

| 項目 | Before | After |
|------|--------|-------|
| **設定の場所** | 分散（各ファイル） | 一元管理（Container） |
| **プロバイダー切り替え** | コード変更が必要 | 設定変更のみ |
| **シングルトン管理** | 手動実装 | 自動管理 |
| **テスト時の依存注入** | 手動注入 | 自動注入 |
| **設定の検証** | なし | 型チェック |

### コードの簡潔性

**Before (手動DI)**:
```python
# 各所で依存性を手動管理（約15行）
from src.core.factory import ProviderFactory
from src.workflows.atomic.chat import ChatWorkflow
from src.core.config import settings

provider = ProviderFactory.create_llm_provider(
    provider_type="gemini",
    config={
        "api_key": settings.gemini_api_key,
        "model": "gemini-2.0-flash-exp"
    }
)

workflow = ChatWorkflow(llm_provider=provider)
result = await workflow.run(input_data)
```

**After (DIコンテナ)**:
```python
# 設定は一度だけ、使用は簡単（約3行）
from src.core.containers import get_chat_workflow

workflow = get_chat_workflow()
result = await workflow.run(input_data)
```

---

## 🧪 テストコード

**新規テストファイル**: `tests/test_di_container.py`

```python
def test_gemini_provider_creation():
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

def test_provider_switching():
    """プロバイダーの動的切り替えテスト"""
    container = Container()
    
    # Geminiプロバイダー
    container.config.llm_provider_type.from_value('gemini')
    provider1 = container.llm_provider()
    assert isinstance(provider1, GeminiProvider)
    
    # Mockプロバイダーに切り替え
    container.config.llm_provider_type.from_value('mock')
    provider2 = container.llm_provider()
    assert isinstance(provider2, MockLLMProvider)

def test_workflow_creation_with_di():
    """DIコンテナを使用したワークフロー作成テスト"""
    container = Container()
    container.config.from_dict({
        'llm_provider_type': 'mock',
        'mock': {'responses': {'test': 'response'}}
    })
    
    workflow = container.chat_workflow()
    assert workflow is not None
    assert isinstance(workflow.llm_node.provider, MockLLMProvider)
```

**テストケース**: 11個
- ✅ コンテナの作成
- ✅ プロバイダーの作成
- ✅ プロバイダーの切り替え
- ✅ シングルトンの動作
- ✅ グローバルコンテナ
- ✅ ワークフロー作成
- ✅ ノード作成
- ✅ 設定のオーバーライド
- ✅ コンテナの独立性
- ✅ 便利関数
- ✅ 後方互換性

---

## 🔧 インストールと使用方法

### 1. ライブラリのインストール

```bash
# dependency-injectorをインストール
pip install -r requirements.txt

# または個別にインストール
pip install dependency-injector>=4.41.0
```

### 2. 基本的な使用方法

```python
# 方法1: グローバルコンテナを使用（推奨）
from src.core.containers import get_llm_provider

provider = get_llm_provider()
response = await provider.generate("Hello!")
```

```python
# 方法2: カスタムコンテナを作成
from src.core.containers import Container

container = Container()
container.config.from_dict({
    'llm_provider_type': 'gemini',
    'gemini': {'api_key': 'xxx', 'model': 'gemini-2.0-flash-exp'}
})

provider = container.llm_provider()
```

```python
# 方法3: 既存のProviderFactory（後方互換）
from src.core.factory import ProviderFactory

# 内部的にDIコンテナを使用
provider = ProviderFactory.get_default_llm_provider()
```

### 3. テストでの使用

```python
import pytest
from src.core.containers import Container, reset_container

class TestMyFeature:
    def setup_method(self):
        """各テスト前にコンテナをリセット"""
        reset_container()
    
    def test_with_mock(self):
        """モックプロバイダーを使用したテスト"""
        container = Container()
        container.config.from_dict({
            'llm_provider_type': 'mock',
            'mock': {'responses': {'Hello': 'Hi!'}}
        })
        
        workflow = container.chat_workflow()
        # テスト実行...
```

---

## 📈 アーキテクチャの進化

### Before（Factory Pattern）

```
Application
    ↓
ProviderFactory.create_llm_provider()
    ↓
Manual instantiation
```

**問題点**:
- 依存性の管理が分散
- 設定の重複
- テスト時の切り替えが面倒

### After（DI Container）

```
Application
    ↓
Container
    ├── Configuration (一元管理)
    ├── Provider Layer (Singleton)
    ├── Node Layer (Factory)
    └── Workflow Layer (Factory)
        ↓
Automatic dependency injection
```

**メリット**:
- 依存性が一元管理
- 設定が統一
- 自動注入
- シングルトン管理

---

## 🎯 達成した目標

### 1. ✅ 依存性の一元管理

- 全ての依存性がContainerで管理される
- 設定が1箇所に集約
- 重複コードの削除

### 2. ✅ 設定ベースの構成

- 設定ファイルからの読み込みが容易
- 環境ごとの切り替えが簡単
- 型安全な設定

### 3. ✅ テスト容易性の向上

- モックプロバイダーへの切り替えが簡単
- テスト用コンテナの独立性
- リセット機能

### 4. ✅ 後方互換性の維持

- 既存のProviderFactoryも動作
- 段階的な移行が可能
- フォールバック機能

### 5. ✅ エンタープライズグレードのDI

- dependency-injectorは業界標準
- Pythonコミュニティで広く使用
- 豊富なドキュメントとサポート

---

## 🔮 今後の拡張

### 1. 設定ファイルからの自動読み込み

```python
# config.yaml
llm_provider_type: gemini
gemini:
  api_key: ${GEMINI_API_KEY}
  model: gemini-2.0-flash-exp

# Python
container.config.from_yaml('config.yaml')
```

### 2. スコープベースの管理

```python
# リクエストスコープ
request_container = containers.copy()
request_container.config.user_id.from_value(user_id)
```

### 3. 自動ワイヤリング（Autowiring）

```python
from dependency_injector.wiring import inject, Provide

@inject
async def my_function(
    provider: LLMProvider = Provide[Container.llm_provider]
):
    response = await provider.generate("Hello")
```

### 4. 環境別設定の自動切り替え

```python
# 環境変数から自動判定
ENV = os.getenv('ENVIRONMENT', 'development')

if ENV == 'development':
    container.config.from_yaml('config.dev.yaml')
elif ENV == 'production':
    container.config.from_yaml('config.prod.yaml')
```

---

## 📚 参考リソース

- [dependency-injector公式ドキュメント](https://python-dependency-injector.ets-labs.org/)
- [Dependency Injection in Python](https://www.martinfowler.com/articles/injection.html)
- [Python DIパターンのベストプラクティス](https://realpython.com/dependency-injection-python/)

---

## ✅ まとめ

DIコンテナの導入により、以下を達成しました：

1. **依存性の一元管理** - Container で全ての依存性を管理
2. **設定の統一** - 設定が1箇所に集約
3. **自動注入** - ワークフロー、ノードの依存性を自動注入
4. **テスト容易性** - モックへの切り替えが簡単
5. **後方互換性** - 既存コードは変更不要
6. **エンタープライズグレード** - 業界標準のDIライブラリを使用

このプロジェクトは、**最先端のDIパターン**を実装し、保守性と拡張性が大幅に向上しました。

---

*完了日: 2025年11月22日*  
*ステータス: ✅ 全改善完了*

