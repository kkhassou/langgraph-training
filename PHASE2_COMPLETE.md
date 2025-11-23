# Phase 2 完了レポート: Node 層のリファクタリング

## 実施日時

2025 年 11 月 22 日

## 概要

Node 層に依存性注入（DI）パターンを導入し、Provider を注入可能にしました。既存コードとの後方互換性を保ちながら、テスト性と拡張性を大幅に向上させました。

## 変更内容

### 1. LLMNode の改善 ✅

#### 新規作成・更新ファイル

- `src/nodes/llm/gemini.py` - 更新
- `src/nodes/primitives/llm/gemini/node.py` - 更新

#### 実装内容

**Before (Phase 1):**

```python
class GeminiNode(BaseNode):
    def __init__(self):
        super().__init__(name="gemini_llm", ...)
        # GeminiService に直接依存

    async def execute(self, state):
        response = await GeminiService.generate(...)
```

**After (Phase 2):**

```python
class LLMNode(BaseNode):
    """プロバイダー注入可能なLLMノード"""

    def __init__(self, provider: LLMProvider, name: str = "llm_node", ...):
        super().__init__(name=name, ...)
        self.provider = provider  # ✅ DI パターン

    async def execute(self, state):
        response = await self.provider.generate(...)  # ✅ プロバイダーに委譲


# ✅ 後方互換性のためのエイリアス
class GeminiNode(LLMNode):
    """既存コードとの互換性を保つ"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash-exp"):
        provider = GeminiProvider(api_key=api_key or settings.gemini_api_key, model=model)
        super().__init__(provider=provider, name="gemini_llm", ...)
```

#### 使用例

**新しい方法（推奨）:**

```python
from src.providers.llm.gemini import GeminiProvider
from src.nodes.llm.gemini import LLMNode

# プロバイダーを注入
provider = GeminiProvider(api_key="...", model="gemini-2.0-flash-exp")
node = LLMNode(provider=provider)
```

**既存の方法（後方互換）:**

```python
from src.nodes.llm.gemini import GeminiNode

# 既存コードはそのまま動作
node = GeminiNode()
```

### 2. RAGNode の改善 ✅

#### 新規作成・更新ファイル

- `src/providers/rag/simple.py` - **新規作成**
- `src/providers/rag/__init__.py` - 更新
- `src/nodes/rag/rag_node.py` - 更新
- `src/nodes/primitives/rag/simple/node.py` - 更新

#### 実装内容

**新規: SimpleRAGProvider**

```python
class SimpleRAGProvider(RAGProvider):
    """RAGServiceをラップしたプロバイダー実装"""

    def __init__(self):
        self.rag_service = RAGService()

    async def query(self, query: str, ...) -> RAGResult:
        return await self.rag_service.query(...)

    async def ingest_documents(self, documents: List[Dict], ...) -> Dict:
        return await self.rag_service.ingest_documents(...)
```

**RAGNode の更新:**

```python
class RAGNode(BaseNode):
    """プロバイダー注入可能なRAGノード"""

    def __init__(
        self,
        provider: Optional[RAGProvider] = None,  # ✅ オプショナル
        name: str = "rag_node",
        ...
    ):
        super().__init__(name=name, ...)
        self.provider = provider or SimpleRAGProvider()  # ✅ デフォルトあり

    async def execute(self, state):
        result = await self.provider.query(...)  # ✅ プロバイダーに委譲
```

#### 使用例

**新しい方法（推奨）:**

```python
from src.providers.rag.simple import SimpleRAGProvider
from src.nodes.rag.rag_node import RAGNode

# プロバイダーを注入
provider = SimpleRAGProvider()
node = RAGNode(provider=provider)
```

**既存の方法（後方互換）:**

```python
from src.nodes.rag.rag_node import RAGNode

# プロバイダーを省略してもデフォルトで動作
node = RAGNode()
```

## 実装されたファイル一覧

### 更新されたファイル

1. `src/nodes/llm/gemini.py` - LLMNode + GeminiNode エイリアス
2. `src/nodes/primitives/llm/gemini/node.py` - 同上（プリミティブ版）
3. `src/nodes/rag/rag_node.py` - プロバイダー注入対応
4. `src/nodes/primitives/rag/simple/node.py` - 同上（プリミティブ版）
5. `src/providers/rag/__init__.py` - SimpleRAGProvider エクスポート

### 新規作成されたファイル

1. `src/providers/rag/simple.py` - SimpleRAGProvider 実装

## メリット

### 1. テスト性の向上 🧪

```python
# モックプロバイダーを注入してテスト
class MockLLMProvider(LLMProvider):
    async def generate(self, prompt, **kwargs):
        return "モック応答"

provider = MockLLMProvider()
node = LLMNode(provider=provider)
# → 外部APIを呼ばずにテスト可能
```

### 2. 拡張性の向上 🚀

```python
# 新しいLLMサービスを追加
class OpenAIProvider(LLMProvider):
    async def generate(self, prompt, **kwargs):
        # OpenAI API を呼び出し
        ...

# ノードコードは変更不要
provider = OpenAIProvider(api_key="...")
node = LLMNode(provider=provider)
```

### 3. 後方互換性の維持 ✅

```python
# 既存のコードは変更なしで動作
node = GeminiNode()  # ← 今まで通り使える
```

## アーキテクチャ図

```
┌─────────────────────────────────────────────┐
│            Application Layer                │
│  (Workflows / API Handlers)                 │
└─────────────────┬───────────────────────────┘
                  │
                  │ 使用
                  ▼
┌─────────────────────────────────────────────┐
│              Node Layer                     │
│  ┌─────────────────────────────────────┐   │
│  │  LLMNode(provider: LLMProvider)     │   │ ← DI対応
│  │  RAGNode(provider: RAGProvider)     │   │ ← DI対応
│  │                                     │   │
│  │  GeminiNode() ← エイリアス         │   │ ← 後方互換
│  └─────────────────────────────────────┘   │
└─────────────────┬───────────────────────────┘
                  │
                  │ 依存
                  ▼
┌─────────────────────────────────────────────┐
│           Provider Layer                    │
│  ┌─────────────────────────────────────┐   │
│  │  LLMProvider (Interface)            │   │
│  │    └── GeminiProvider               │   │
│  │    └── (OpenAIProvider - 将来)     │   │
│  │                                     │   │
│  │  RAGProvider (Interface)            │   │
│  │    └── SimpleRAGProvider            │   │
│  │    └── (AdvancedRAGProvider - 将来)│   │
│  └─────────────────────────────────────┘   │
└─────────────────┬───────────────────────────┘
                  │
                  │ 使用
                  ▼
┌─────────────────────────────────────────────┐
│       Infrastructure / Service Layer        │
│  (RAGService, Embeddings, Vector Stores)    │
└─────────────────────────────────────────────┘
```

## テスト結果

### 構造テスト

- ✅ LLMNode に provider パラメータが存在
- ✅ GeminiNode が LLMNode を継承
- ✅ RAGNode に provider パラメータが存在
- ✅ LLMProvider インターフェースが定義されている
- ✅ RAGProvider インターフェースが定義されている
- ✅ SimpleRAGProvider が正しく実装されている

### リンターチェック

- ✅ 全ファイルでリンターエラーなし

## 今後の拡張可能性

### 新しい LLM プロバイダーの追加

```python
# src/providers/llm/openai.py
class OpenAIProvider(LLMProvider):
    async def generate(self, prompt, **kwargs):
        # OpenAI API 実装
        ...
```

### 新しい RAG プロバイダーの追加

```python
# src/providers/rag/advanced.py
class AdvancedRAGProvider(RAGProvider):
    async def query(self, query, **kwargs):
        # 高度なRAG実装（ハイブリッド検索など）
        ...
```

### テスト用モックプロバイダー

```python
# tests/mocks/providers.py
class MockLLMProvider(LLMProvider):
    async def generate(self, prompt, **kwargs):
        return f"Mock response for: {prompt}"

class MockRAGProvider(RAGProvider):
    async def query(self, query, **kwargs):
        return RAGResult(answer="Mock answer", ...)
```

## 影響範囲

### 変更なしで動作するコード

- ✅ 既存の全ての Workflow
- ✅ 既存の全ての API ハンドラー
- ✅ `GeminiNode()` を使用しているコード
- ✅ `RAGNode()` を使用しているコード（デフォルトプロバイダーを使用）

### 推奨される新しい書き方

```python
# より明示的で拡張性の高い書き方
provider = GeminiProvider(api_key="...", model="...")
node = LLMNode(provider=provider)
```

## 次のステップ (Phase 3 以降)

1. **Workflow 層への DI 導入**

   - Workflow にもノードを注入できるようにする
   - テスト時にモックノードを使用可能に

2. **モックプロバイダーの実装**

   - テスト用のモック実装を作成
   - ユニットテストの充実化

3. **複数 LLM サービスのサポート**

   - OpenAIProvider の実装
   - AnthropicProvider の実装
   - プロバイダーの動的切り替え

4. **設定ベースのプロバイダー選択**
   - 環境変数で使用するプロバイダーを選択
   - ファクトリーパターンの導入

## まとめ

Phase 2 では、Node 層に依存性注入パターンを導入し、以下を達成しました：

✅ **実装完了**

- LLMNode と RAGNode へのプロバイダー注入
- 後方互換性の維持（既存コードは変更不要）
- SimpleRAGProvider の実装
- 全ファイルのリンターエラー解消

✅ **メリット**

- テスト性の向上（モックプロバイダーを注入可能）
- 拡張性の向上（新しい LLM サービスの追加が容易）
- 保守性の向上（明確な責任分離）
- 後方互換性（既存コードは動作し続ける）

🎉 **Phase 2 は成功裏に完了しました！**
