# Services Layer - 高レベルな統合サービス

このディレクトリは、複数のプロバイダーやインフラ層を統合する高レベルなサービスを含みます。

## 📊 アーキテクチャにおける位置づけ

```
┌─────────────────────────────────┐
│   Workflows Layer               │  ← 実行可能なグラフ
│   (workflows/atomic/composite)  │
└──────────────┬──────────────────┘
               ↓ 使う
┌─────────────────────────────────┐
│   Nodes Layer                   │  ← LangGraphノード定義
│   (nodes/primitives/composites) │
└──────────────┬──────────────────┘
               ↓ 使う
┌─────────────────────────────────┐
│   Providers Layer               │  ← 抽象インターフェース
│   (core/providers, providers/)  │     (LLM, RAGなど)
└──────────────┬──────────────────┘
               ↓ 使う
┌─────────────────────────────────┐
│   Services Layer ⭐ ここ！       │  ← 統合サービス
│   (services/rag/mcp/document)   │     (複数プロバイダーを統合)
└──────────────┬──────────────────┘
               ↓ 使う
┌─────────────────────────────────┐
│   Infrastructure Layer          │  ← 低レベル実装
│   (embeddings, vector_stores)   │
└─────────────────────────────────┘
```

## 🎯 Services 層の新しい役割（リファクタリング後）

### ⚠️ 重要な変更

**LLM Service Layer は廃止されました。** LLM関連の機能は Provider Layer に統合されました。

### 現在の役割

Services Layer は以下の **統合サービス** のみを提供します：

1. **RAG Service** - embedding生成、検索、LLM生成を統合
2. **MCP Service** - MCP関連の統合機能（今後）
3. **Document Service** - ドキュメント処理の統合機能（今後）

### 判断基準

**「この機能は複数のプロバイダーやインフラ層を統合するか？」** → YES なら Services

## 📁 ディレクトリ構造（リファクタリング後）

```
src/services/
│
├── llm/                    # ❌ 廃止 → src/core/providers/llm へ移行
│   └── __init__.py         # 廃止のお知らせと移行ガイド
│
├── rag/                    # ✅ 統合サービスとして残す
│   ├── __init__.py
│   └── rag_service.py      # Embedding + VectorStore + LLM の統合
│
├── mcp/                    # ✅ MCP統合サービス
│   ├── __init__.py
│   ├── slack.py
│   ├── github.py
│   └── google/...
│
└── document/               # ✅ ドキュメント処理サービス
    ├── __init__.py
    └── document_service.py
```

## 💡 使用例

### ⚠️ LLM Services は廃止されました

**旧コード（廃止）:**
```python
from src.services.llm.gemini_service import GeminiService

# ❌ この方法は使用しないでください
advice = await GeminiService.generate(prompt=prompt, temperature=0.7)
```

**新しいコード（推奨）:**
```python
from src.core.factory import ProviderFactory

# ✅ Providerパターンを使用
provider = ProviderFactory.get_default_llm_provider()
advice = await provider.generate(prompt=prompt, temperature=0.7)
```

### RAG Services（統合サービス）

#### RAGクエリの実行

```python
from src.services.rag.rag_service import RAGService

# RAGサービスを初期化
service = RAGService()

# クエリを実行（embedding生成、検索、LLM生成を統合）
result = await service.query(
    query="機械学習とは？",
    collection_name="tech_docs",
    top_k=5
)

print(result.answer)  # LLMの応答
print(result.retrieved_documents)  # 検索結果
```

#### ドキュメントの登録

```python
from src.services.rag.rag_service import RAGService

service = RAGService()

documents = [
    {
        "id": "doc1",
        "content": "機械学習は...",
        "metadata": {"source": "textbook"}
    }
]

result = await service.ingest_documents(
    documents=documents,
    collection_name="tech_docs"
)
```

## 📝 LLM Provider API リファレンス（移行先）

### ⚠️ LLM関連は Provider Layer へ移行しました

LLM機能は `src.core.providers.llm.LLMProvider` インターフェースに統合されています。

**新しい使い方:**

```python
from src.core.factory import ProviderFactory

# Providerを取得
provider = ProviderFactory.get_default_llm_provider()

# テキスト生成
text = await provider.generate(
    prompt="こんにちは",
    temperature=0.7
)

# JSON生成
from pydantic import BaseModel

class TodoItem(BaseModel):
    title: str
    priority: str

result = await provider.generate_json(
    prompt="TODOを作成してください",
    schema=TodoItem,
    temperature=0.7
)

# コンテキスト付き生成
answer = await provider.generate_with_context(
    user_query="機械学習とは？",
    context="機械学習は...",
    system_instruction="専門家として回答してください",
    temperature=0.7
)
```

詳細は以下を参照：
- `src/core/providers/llm.py` - LLMProviderインターフェース
- `src/providers/llm/gemini.py` - Gemini実装
- `src/core/factory.py` - ProviderFactory

## 📝 RAG Service API リファレンス

### `RAGService.query()`

RAGクエリを実行（embedding生成、検索、LLM生成を統合）

**パラメータ**:

- `query: str` - ユーザーの質問
- `collection_name: str = "default_collection"` - 検索対象のコレクション
- `top_k: int = 5` - 取得するドキュメント数
- `include_embedding: bool = False` - 埋め込みベクトルを含めるか
- `temperature: float = 0.7` - LLMの温度パラメータ

**戻り値**: `RAGResult` - RAG実行結果

### `RAGService.ingest_documents()`

ドキュメントをVector Storeに登録

**パラメータ**:

- `documents: List[Dict[str, Any]]` - ドキュメントのリスト
- `collection_name: str = "default_collection"` - コレクション名

**戻り値**: `Dict[str, Any]` - 登録結果

## 🎁 メリット（Provider パターンへの移行後）

### Before（直接API呼び出し）

```python
# 各ノードで36行の重複コード
class TodoAdvisorNode:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    async def execute(self, input_data):
        response = self.model.generate_content(prompt)
        advice = response.text.strip()
        # ...
```

### After（Provider パターン + 依存性注入）

```python
# シンプルで拡張可能
class TodoAdvisorNode:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or ProviderFactory.get_default_llm_provider()
    
    async def execute(self, input_data):
        prompt = self._create_prompt(input_data["todo"])
        advice = await self.provider.generate(prompt, temperature=0.7)
        return NodeResult(success=True, data={"advice": advice})
```

**結果**: 
- コードが 60%削減
- テスト時にモック注入が可能
- 異なるLLMへの切り替えが容易
- 保守性・拡張性が大幅に向上！

## 🚀 今後の拡張

### 新しいLLM Providerの追加（Provider Layer）

```python
# src/providers/llm/openai.py
from src.core.providers.llm import LLMProvider

class OpenAIProvider(LLMProvider):
    async def generate(self, prompt: str, **kwargs) -> str:
        # OpenAI実装
        ...

# 登録
from src.core.factory import ProviderFactory
ProviderFactory.register_llm_provider("openai", OpenAIProvider)
```

### RAG統合サービスの強化

```python
# src/services/rag/advanced_rag_service.py
class AdvancedRAGService(RAGService):
    """より高度な検索・生成機能を持つRAGサービス"""
    async def query_with_reranking(self, query: str, **kwargs):
        # リランキング機能を追加
        ...
```

### MCP統合サービス

```python
# src/services/mcp/unified_mcp_service.py
class UnifiedMCPService:
    """複数のMCPサービスを統合"""
    async def execute_workflow(self, workflow: Dict[str, Any]):
        # Slack + GitHub + Google の統合ワークフロー
        ...
```

## 📚 関連ドキュメント

- [リファクタリング完了レポート](../../REFACTORING_COMPLETE.md)
- [Provider層の設計](../../PHASE1_COMPLETE.md)
- [Factory パターン](../../PHASE4_COMPLETE.md)
- [アーキテクチャ概要](../../拡張性を考慮したアーキテクトへのアドバイス.md)
