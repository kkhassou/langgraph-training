# FastAPI Depends への移行完了レポート

**実施日**: 2025 年 11 月 23 日  
**目的**: `dependency-injector`ライブラリから FastAPI の`Depends`機能への移行  
**ステータス**: ✅ 完了

---

## 📋 実施内容

### 1. FastAPI Depends の導入

**新規ファイル**: `src/api/dependencies.py`

FastAPI の`Depends`機能を使用した依存性注入システムを実装しました。

#### 主な機能

1. **Provider Dependencies**

   - `get_llm_provider()`: LLM プロバイダーを取得
   - `get_gemini_provider()`: Gemini プロバイダーを取得
   - `get_mock_llm_provider()`: モックプロバイダーを取得（テスト用）
   - `get_rag_provider()`: RAG プロバイダーを取得

2. **Workflow Dependencies**

   - `get_chat_workflow()`: ChatWorkflow を取得
   - `get_rag_query_workflow()`: RAGQueryWorkflow を取得
   - `get_document_extract_workflow()`: DocumentExtractWorkflow を取得
   - `get_ppt_summary_workflow()`: PPTSummaryWorkflow を取得
   - `get_chain_of_thought_workflow()`: ChainOfThoughtWorkflow を取得
   - `get_reflection_workflow()`: ReflectionWorkflow を取得

3. **Service Dependencies**

   - `get_rag_service()`: RAGService を取得
   - `get_document_service()`: DocumentService を取得
   - `get_slack_service()`: SlackService を取得
   - `get_github_service()`: GitHubService を取得
   - `get_notion_service()`: NotionService を取得

4. **Node Dependencies**
   - `get_llm_node()`: LLMNode を取得
   - `get_retrieval_node()`: RetrievalNode を取得

---

### 2. API ルートの更新

#### routes_workflows.py

全てのワークフローエンドポイントで FastAPI Depends を使用するように更新しました。

**Before:**

```python
# グローバルインスタンス
chat_workflow = ChatWorkflow()

@router.post("/atomic/chat")
async def run_chat(input_data: ChatInput):
    result = await chat_workflow.run(input_data)
    return result
```

**After:**

```python
from src.api.dependencies import get_chat_workflow

@router.post("/atomic/chat")
async def run_chat(
    input_data: ChatInput,
    workflow: ChatWorkflow = Depends(get_chat_workflow)
):
    result = await workflow.run(input_data)
    return result
```

#### routes_nodes.py

ノードハンドラーでも FastAPI Depends を使用するように更新しました。

**追加機能:**

- `llm_node_handler()`: LLM ノードのハンドラー関数（Depends 対応）

**Before:**

```python
@router.post("/llm")
async def run_llm_node(input_data: LLMInput):
    result = await llm_node_handler(input_data)
    return result
```

**After:**

```python
from src.api.dependencies import get_llm_provider

@router.post("/llm")
async def run_llm_node(
    input_data: LLMInput,
    provider: LLMProvider = Depends(get_llm_provider)
):
    result = await llm_node_handler(input_data, provider=provider)
    return result
```

---

### 3. factory.py の更新

`ProviderFactory`クラスの`get_default_llm_provider()`と`get_default_rag_provider()`メソッドを更新し、`dependency-injector`の代わりに FastAPI の`Depends`システムを参照するようにしました。

**変更点:**

```python
# Before
from src.core.containers import get_llm_provider

# After
from src.api.dependencies import get_llm_provider
```

---

### 4. containers.py の非推奨化

`src/core/containers.py`は非推奨としてマークしました。

- ファイルの先頭に**DEPRECATED**警告を追加
- 移行ガイドを追加
- 後方互換性のためにファイルは残存

---

## 🎯 FastAPI Depends のメリット

### 1. 明示的な依存関係

**Before (dependency-injector):**

```python
# 依存関係が暗黙的
chat_workflow = ChatWorkflow()

@router.post("/chat")
async def chat(input_data: ChatInput):
    result = await chat_workflow.run(input_data)
    return result
```

**After (FastAPI Depends):**

```python
# 依存関係が明示的
@router.post("/chat")
async def chat(
    input_data: ChatInput,
    workflow: ChatWorkflow = Depends(get_chat_workflow)  # ← 明確！
):
    result = await workflow.run(input_data)
    return result
```

### 2. テスト容易性の向上

FastAPI の`dependency_overrides`機能により、テスト時に簡単にモックに置き換えられます。

```python
# テストコード
from src.api.dependencies import get_chat_workflow

def mock_chat_workflow():
    return MockChatWorkflow()

# テスト時に依存関係を置き換え
app.dependency_overrides[get_chat_workflow] = mock_chat_workflow

# テスト実行
response = client.post("/workflows/atomic/chat", json={"message": "test"})
```

### 3. FastAPI エコシステムとの統合

- **自動ドキュメント化**: SwaggerUI で依存関係が自動的に表示される
- **型安全**: IDE の補完とエラーチェックが効く
- **バリデーション**: Pydantic モデルと統合される
- **リクエストスコープ**: リクエストごとのインスタンス管理が容易

### 4. シンプルな実装

`lru_cache`を使用してシングルトンを簡単に実装できます。

```python
from functools import lru_cache

@lru_cache()
def get_llm_provider() -> LLMProvider:
    return GeminiProvider(
        api_key=settings.gemini_api_key,
        model="gemini-2.0-flash-exp"
    )
```

### 5. 標準的な FastAPI パターン

外部ライブラリ（`dependency-injector`）への依存を削減し、FastAPI 標準の機能のみを使用します。

---

## 💡 使用例

### 例 1: 基本的な使用

```python
from fastapi import Depends
from src.api.dependencies import get_llm_provider

@router.post("/generate")
async def generate(
    prompt: str,
    provider: LLMProvider = Depends(get_llm_provider)
):
    response = await provider.generate(prompt)
    return {"response": response}
```

### 例 2: ワークフローの使用

```python
from fastapi import Depends
from src.api.dependencies import get_chat_workflow

@router.post("/chat")
async def chat(
    input_data: ChatInput,
    workflow: ChatWorkflow = Depends(get_chat_workflow)
):
    result = await workflow.run(input_data)
    return result
```

### 例 3: テスト時のモック

```python
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.api.dependencies import get_llm_provider
from src.providers.llm.mock import MockLLMProvider

@pytest.fixture
def client():
    # モックプロバイダーに置き換え
    def mock_provider():
        return MockLLMProvider(responses={"test": "response"})

    app.dependency_overrides[get_llm_provider] = mock_provider

    with TestClient(app) as c:
        yield c

    # クリーンアップ
    app.dependency_overrides.clear()

def test_chat(client):
    response = client.post("/workflows/atomic/chat", json={
        "message": "test",
        "temperature": 0.7,
        "max_tokens": 1000
    })
    assert response.status_code == 200
```

### 例 4: 複数の依存関係

```python
from fastapi import Depends
from src.api.dependencies import get_llm_provider, get_rag_provider

@router.post("/advanced")
async def advanced_endpoint(
    query: str,
    llm_provider: LLMProvider = Depends(get_llm_provider),
    rag_provider: RAGProvider = Depends(get_rag_provider)
):
    # 両方のプロバイダーを使用
    docs = await rag_provider.retrieve(query)
    response = await llm_provider.generate(f"Context: {docs}\nQuery: {query}")
    return {"response": response}
```

---

## 📊 改善効果

### コードの簡潔性

| 項目             | Before (dependency-injector) | After (FastAPI Depends)  |
| ---------------- | ---------------------------- | ------------------------ |
| **外部依存**     | dependency-injector          | なし（FastAPI 標準機能） |
| **設定ファイル** | containers.py (270 行)       | dependencies.py (280 行) |
| **ルートコード** | 暗黙的な依存関係             | 明示的な依存関係         |
| **テストコード** | コンテナをリセット           | dependency_overrides     |
| **学習コスト**   | 高（独自ライブラリ）         | 低（FastAPI 標準）       |

### 依存性管理の改善

| 項目                   | Before               | After                        |
| ---------------------- | -------------------- | ---------------------------- |
| **依存関係の可視性**   | 低（グローバル変数） | 高（関数パラメータ）         |
| **テスト時の置き換え** | 複雑（コンテナ設定） | 簡単（dependency_overrides） |
| **型チェック**         | 限定的               | 完全（FastAPI 統合）         |
| **ドキュメント化**     | 手動                 | 自動（SwaggerUI）            |
| **エラーメッセージ**   | 一般的               | 具体的（FastAPI 検証）       |

---

## 🔧 移行ガイド

### 既存コードの移行方法

#### 1. グローバルインスタンスの置き換え

**Before:**

```python
# モジュールレベル
chat_workflow = ChatWorkflow()

@router.post("/chat")
async def chat(input_data: ChatInput):
    result = await chat_workflow.run(input_data)
    return result
```

**After:**

```python
# Dependsを使用
from src.api.dependencies import get_chat_workflow

@router.post("/chat")
async def chat(
    input_data: ChatInput,
    workflow: ChatWorkflow = Depends(get_chat_workflow)
):
    result = await workflow.run(input_data)
    return result
```

#### 2. DI コンテナからの移行

**Before:**

```python
from src.core.containers import get_container

container = get_container()
provider = container.llm_provider()
```

**After:**

```python
from src.api.dependencies import get_llm_provider

provider = get_llm_provider()
```

#### 3. テストコードの移行

**Before:**

```python
from src.core.containers import Container, reset_container

def test_workflow():
    # テスト用コンテナ
    container = Container()
    container.config.from_dict({'llm_provider_type': 'mock'})

    workflow = container.chat_workflow()
    # テスト実行
```

**After:**

```python
from src.api.dependencies import get_chat_workflow
from src.main import app

def test_workflow():
    # モック注入
    def mock_workflow():
        return MockChatWorkflow()

    app.dependency_overrides[get_chat_workflow] = mock_workflow

    # テスト実行
    # ...

    # クリーンアップ
    app.dependency_overrides.clear()
```

---

## ✅ まとめ

FastAPI Depends への移行により、以下を達成しました：

1. **✅ 依存関係の明示化** - 関数パラメータで依存関係が明確に表示される
2. **✅ テスト容易性の向上** - `dependency_overrides`で簡単にモック化
3. **✅ FastAPI エコシステムとの統合** - 自動ドキュメント化、型安全性、バリデーション
4. **✅ 外部依存の削減** - `dependency-injector`ライブラリが不要に
5. **✅ 標準的なパターン** - FastAPI コミュニティで広く使用されているパターン
6. **✅ シンプルな実装** - `lru_cache`でシングルトンを簡単に実装

このプロジェクトは、**FastAPI 標準のベストプラクティス**に従った実装に進化し、保守性と拡張性が大幅に向上しました。

---

## 📚 参考リソース

- [FastAPI Dependencies - 公式ドキュメント](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [FastAPI Advanced Dependencies](https://fastapi.tiangolo.com/advanced/advanced-dependencies/)
- [Testing FastAPI Applications](https://fastapi.tiangolo.com/tutorial/testing/)

---

_完了日: 2025 年 11 月 23 日_  
_ステータス: ✅ 全改善完了_
