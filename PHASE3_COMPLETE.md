# Phase 3 完了レポート: Workflow 層のリファクタリング

## 実施日時

2025 年 11 月 22 日

## 概要

Workflow 層に依存性注入（DI）パターンを導入し、プロバイダーを注入可能にしました。既存コードとの後方互換性を保ちながら、テスト性と拡張性を大幅に向上させました。

## 変更内容

### 1. Atomic Workflow の改善 ✅

#### 1.1 ChatWorkflow の更新

**ファイル**: `src/workflows/atomic/chat.py`

**Before (Phase 2):**

```python
class ChatWorkflow:
    def __init__(self):
        self.llm_node = GeminiNode()  # 直接 GeminiNode に依存
        self.graph = self._build_graph()
```

**After (Phase 3):**

```python
class ChatWorkflow:
    """チャットワークフロー（プロバイダー注入可能）"""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        # ✅ プロバイダーが指定されなければデフォルトを使用
        if llm_provider is None:
            llm_provider = GeminiProvider(
                api_key=settings.gemini_api_key,
                model="gemini-2.0-flash-exp"
            )

        self.llm_node = LLMNode(provider=llm_provider, name="chat_llm")
        self.graph = self._build_graph()
```

**使用例:**

```python
# 新しい方法（推奨）
from src.providers.llm.gemini import GeminiProvider
from src.workflows.atomic.chat import ChatWorkflow

provider = GeminiProvider(api_key="...", model="...")
workflow = ChatWorkflow(llm_provider=provider)

# 既存の方法（後方互換）
workflow = ChatWorkflow()  # デフォルトプロバイダーを使用
```

#### 1.2 RAGQueryWorkflow の更新

**ファイル**: `src/workflows/atomic/rag_query.py`

**Before (Phase 2):**

```python
class RAGQueryWorkflow:
    def __init__(self):
        self.rag_node = RAGNode()  # 直接 RAGNode に依存
        self.graph = self._build_graph()
```

**After (Phase 3):**

```python
class RAGQueryWorkflow:
    """RAG検索ワークフロー（プロバイダー注入可能）"""

    def __init__(self, rag_provider: Optional[RAGProvider] = None):
        # ✅ プロバイダーが指定されなければデフォルトを使用
        if rag_provider is None:
            rag_provider = SimpleRAGProvider()

        self.rag_node = RAGNode(provider=rag_provider, name="rag_query")
        self.graph = self._build_graph()
```

**使用例:**

```python
# 新しい方法（推奨）
from src.providers.rag.simple import SimpleRAGProvider
from src.workflows.atomic.rag_query import RAGQueryWorkflow

provider = SimpleRAGProvider()
workflow = RAGQueryWorkflow(rag_provider=provider)

# 既存の方法（後方互換）
workflow = RAGQueryWorkflow()  # デフォルトプロバイダーを使用
```

### 2. Composite Workflow の改善 ✅

#### 2.1 ChainOfThoughtWorkflow の更新

**ファイル**: `src/workflows/composite/intelligent_chat/chain_of_thought.py`

```python
class ChainOfThoughtWorkflow:
    """Chain of Thought（段階的推論）ワークフロー（プロバイダー注入可能）"""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        # ✅ Atomic Workflow にプロバイダーを注入
        self.chat = ChatWorkflow(llm_provider=llm_provider)
```

#### 2.2 ReflectionWorkflow の更新

**ファイル**: `src/workflows/composite/intelligent_chat/reflection.py`

```python
class ReflectionWorkflow:
    """Reflection（自己批判的推論）ワークフロー（プロバイダー注入可能）"""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        # ✅ Atomic Workflow にプロバイダーを注入
        self.chat = ChatWorkflow(llm_provider=llm_provider)
```

#### 2.3 PPTSummaryWorkflow の更新

**ファイル**: `src/workflows/composite/document_analysis/ppt_summary.py`

```python
class PPTSummaryWorkflow:
    """PowerPoint要約ワークフロー（プロバイダー注入可能）"""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.extractor = DocumentExtractWorkflow()
        # ✅ Chat Workflow にプロバイダーを注入
        self.chat = ChatWorkflow(llm_provider=llm_provider)
```

### 3. 可視化機能の追加 ✅

全ての Atomic Workflow に `get_mermaid_diagram()` メソッドを追加しました。

```python
def get_mermaid_diagram(self) -> str:
    """LangGraphの可視化

    Returns:
        Mermaid形式のグラフ定義
    """
    return self.graph.get_graph().draw_mermaid()
```

## 実装されたファイル一覧

### 更新されたファイル

1. `src/workflows/atomic/chat.py` - プロバイダー注入対応
2. `src/workflows/atomic/rag_query.py` - プロバイダー注入対応
3. `src/workflows/composite/intelligent_chat/chain_of_thought.py` - プロバイダー注入対応
4. `src/workflows/composite/intelligent_chat/reflection.py` - プロバイダー注入対応
5. `src/workflows/composite/document_analysis/ppt_summary.py` - プロバイダー注入対応

## アーキテクチャの進化

### Phase 1 → Phase 2 → Phase 3 の変遷

```
┌─────────────────────────────────────────────┐
│          Application Layer                  │
│  (API Handlers / UI)                        │
└─────────────────┬───────────────────────────┘
                  │
                  │ Phase 3: Workflow にプロバイダー注入
                  ▼
┌─────────────────────────────────────────────┐
│           Workflow Layer                    │
│  ┌─────────────────────────────────────┐   │
│  │ ChatWorkflow(llm_provider)          │   │ ← Phase 3: DI対応
│  │ RAGQueryWorkflow(rag_provider)      │   │ ← Phase 3: DI対応
│  │                                     │   │
│  │ Composite Workflows                 │   │
│  │   └─ ChainOfThoughtWorkflow         │   │ ← Phase 3: DI対応
│  │   └─ ReflectionWorkflow             │   │ ← Phase 3: DI対応
│  └─────────────────────────────────────┘   │
└─────────────────┬───────────────────────────┘
                  │
                  │ Phase 2: Node にプロバイダー注入
                  ▼
┌─────────────────────────────────────────────┐
│              Node Layer                     │
│  ┌─────────────────────────────────────┐   │
│  │ LLMNode(provider: LLMProvider)      │   │ ← Phase 2: DI対応
│  │ RAGNode(provider: RAGProvider)      │   │ ← Phase 2: DI対応
│  └─────────────────────────────────────┘   │
└─────────────────┬───────────────────────────┘
                  │
                  │ Phase 1: Provider の抽象化
                  ▼
┌─────────────────────────────────────────────┐
│           Provider Layer                    │
│  ┌─────────────────────────────────────┐   │
│  │ LLMProvider (Interface)             │   │ ← Phase 1
│  │   └── GeminiProvider                │   │
│  │                                     │   │
│  │ RAGProvider (Interface)             │   │ ← Phase 2
│  │   └── SimpleRAGProvider             │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

## メリット

### 1. テスト性の向上 🧪

```python
# モックプロバイダーでワークフローをテスト
class MockLLMProvider(LLMProvider):
    async def generate(self, prompt, **kwargs):
        return "モック応答"

provider = MockLLMProvider()
workflow = ChatWorkflow(llm_provider=provider)
result = await workflow.run(ChatInput(message="テスト"))
# → 外部APIを呼ばずにテスト可能
```

### 2. 拡張性の向上 🚀

```python
# 異なるLLMサービスを簡単に切り替え
openai_provider = OpenAIProvider(api_key="...")
workflow = ChatWorkflow(llm_provider=openai_provider)

# Composite Workflow も同じプロバイダーを使用
cot_workflow = ChainOfThoughtWorkflow(llm_provider=openai_provider)
```

### 3. 後方互換性の維持 ✅

```python
# 既存のコードは変更なしで動作
workflow = ChatWorkflow()  # ← 今まで通り使える
result = await workflow.run(ChatInput(message="こんにちは"))
```

### 4. 統一的なアーキテクチャ 🏗️

全てのレイヤー（Provider, Node, Workflow）で同じ DI パターンを使用。

## 使用例

### 例 1: シンプルなチャット（デフォルト）

```python
from src.workflows.atomic.chat import ChatWorkflow, ChatInput

# デフォルトプロバイダーを使用
workflow = ChatWorkflow()
result = await workflow.run(ChatInput(message="こんにちは"))
print(result.response)
```

### 例 2: カスタムプロバイダーでチャット

```python
from src.providers.llm.gemini import GeminiProvider
from src.workflows.atomic.chat import ChatWorkflow, ChatInput

# カスタムプロバイダーを注入
provider = GeminiProvider(
    api_key="custom-key",
    model="gemini-pro"
)
workflow = ChatWorkflow(llm_provider=provider)
result = await workflow.run(ChatInput(message="こんにちは"))
```

### 例 3: Composite Workflow でのプロバイダー注入

```python
from src.providers.llm.gemini import GeminiProvider
from src.workflows.composite.intelligent_chat.chain_of_thought import (
    ChainOfThoughtWorkflow, ChainOfThoughtInput
)

# プロバイダーを注入
provider = GeminiProvider(api_key="...", model="...")
workflow = ChainOfThoughtWorkflow(llm_provider=provider)

# 段階的推論を実行
result = await workflow.run(
    ChainOfThoughtInput(
        question="機械学習とディープラーニングの違いは？",
        steps=3
    )
)
print(result.final_answer)
```

### 例 4: テスト用モックプロバイダー

```python
from src.core.providers.llm import LLMProvider
from src.workflows.atomic.chat import ChatWorkflow, ChatInput

class MockLLMProvider(LLMProvider):
    async def generate(self, prompt, **kwargs):
        return f"モック応答: {prompt[:20]}..."

    async def generate_json(self, prompt, schema, **kwargs):
        return schema()

    async def generate_with_context(self, user_query, context, **kwargs):
        return f"モック応答: {user_query}"

# テスト
mock_provider = MockLLMProvider()
workflow = ChatWorkflow(llm_provider=mock_provider)
result = await workflow.run(ChatInput(message="テスト"))
assert result.success
assert "モック応答" in result.response
```

## テスト結果

### リンターチェック

- ✅ 全ファイルでリンターエラーなし
- ✅ 型ヒントが正しく設定されている
- ✅ インポートが正しく整理されている

### 構造チェック

- ✅ ChatWorkflow に `llm_provider` パラメータが存在
- ✅ RAGQueryWorkflow に `rag_provider` パラメータが存在
- ✅ 全ての Composite Workflow がプロバイダー注入をサポート
- ✅ 後方互換性が維持されている（省略時はデフォルト動作）

## 今後の拡張可能性

### 1. プロバイダーファクトリーの導入

```python
# src/core/factories/provider_factory.py
class ProviderFactory:
    @staticmethod
    def create_llm_provider(provider_type: str, **kwargs) -> LLMProvider:
        if provider_type == "gemini":
            return GeminiProvider(**kwargs)
        elif provider_type == "openai":
            return OpenAIProvider(**kwargs)
        elif provider_type == "anthropic":
            return AnthropicProvider(**kwargs)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

# 使用例
provider = ProviderFactory.create_llm_provider(
    provider_type="gemini",
    api_key="...",
    model="gemini-2.0-flash-exp"
)
workflow = ChatWorkflow(llm_provider=provider)
```

### 2. 設定ベースのプロバイダー選択

```python
# config.yaml
llm:
  provider: gemini
  model: gemini-2.0-flash-exp
  temperature: 0.7

rag:
  provider: simple
  top_k: 5
```

### 3. 複数プロバイダーの並行利用

```python
# 複数のLLMに同時にクエリして比較
providers = [
    GeminiProvider(api_key="...", model="gemini-2.0-flash-exp"),
    OpenAIProvider(api_key="...", model="gpt-4"),
]

workflows = [ChatWorkflow(llm_provider=p) for p in providers]
results = await asyncio.gather(*[
    w.run(ChatInput(message="こんにちは")) for w in workflows
])
```

## 影響範囲

### 変更なしで動作するコード

- ✅ 既存の全ての API ハンドラー
- ✅ `ChatWorkflow()` を使用しているコード
- ✅ `RAGQueryWorkflow()` を使用しているコード
- ✅ 全ての Composite Workflow

### 推奨される新しい書き方

```python
# より明示的で拡張性の高い書き方
provider = GeminiProvider(api_key="...", model="...")
workflow = ChatWorkflow(llm_provider=provider)
```

## Phase 1-3 の完全な DI パターン

```python
# Phase 1: Provider の作成
provider = GeminiProvider(api_key="...", model="gemini-2.0-flash-exp")

# Phase 2: Node へプロバイダーを注入
node = LLMNode(provider=provider, name="chat_node")

# Phase 3: Workflow へプロバイダーを注入
workflow = ChatWorkflow(llm_provider=provider)

# 実行
result = await workflow.run(ChatInput(message="こんにちは"))
```

## まとめ

Phase 3 では、Workflow 層に依存性注入パターンを導入し、以下を達成しました：

✅ **実装完了**

- Atomic Workflow（ChatWorkflow, RAGQueryWorkflow）へのプロバイダー注入
- Composite Workflow へのプロバイダー注入
- 後方互換性の維持（既存コードは変更不要）
- 可視化機能の追加（`get_mermaid_diagram()`）
- 全ファイルのリンターエラー解消

✅ **メリット**

- テスト性の向上（モックプロバイダーを注入可能）
- 拡張性の向上（異なる LLM サービスの切り替えが容易）
- 保守性の向上（明確な責任分離）
- 後方互換性（既存コードは動作し続ける）
- 統一的なアーキテクチャ（全レイヤーで同じ DI パターン）

✅ **完成したアーキテクチャ**

```
API Layer
    ↓ (calls)
Workflow Layer ← Phase 3: DI完了
    ↓ (uses)
Node Layer ← Phase 2: DI完了
    ↓ (uses)
Provider Layer ← Phase 1: 抽象化完了
    ↓ (uses)
Infrastructure / Service Layer
```

🎉 **Phase 3 は成功裏に完了しました！**

これで、Provider → Node → Workflow の全レイヤーで依存性注入パターンが統一的に実装され、テスト可能で拡張性の高いアーキテクチャが完成しました。
