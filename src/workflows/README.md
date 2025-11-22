# Workflows - 3 層アーキテクチャ

## 🎯 概要

Workflows 層は、LangGraph を使用して実行可能なワークフローを定義します。
**段階的な合成（Progressive Composition）** の原則に基づき、3 層構造で設計されています。

## 📁 ディレクトリ構造

```
src/workflows/
├── atomic/                          # 原子的ワークフロー（最小の実行可能単位）
│   ├── chat.py                      # シンプルなチャット
│   ├── rag_query.py                 # RAG検索
│   └── document_extract.py          # ドキュメント抽出
│
├── composite/                       # 複合ワークフロー（Atomicの組み合わせ）
│   ├── intelligent_chat/
│   │   ├── chain_of_thought.py     # 段階的推論
│   │   └── reflection.py           # 自己批判的推論
│   ├── document_analysis/
│   │   └── ppt_summary.py          # PPT要約
│   └── todo_management/
│       └── (今後追加予定)
│
└── orchestrations/                  # 統合ワークフロー（Compositeの統合）
    └── (今後追加予定)
```

## 🏗️ 3 層の役割

| 層                 | 役割                       | 例                            | 組み合わせ元              |
| ------------------ | -------------------------- | ----------------------------- | ------------------------- |
| **Atomic**         | 単一機能の最小実行単位     | chat, rag_query               | Nodes 層を使う            |
| **Composite**      | 複数の Atomic を組み合わせ | ppt_summary, chain_of_thought | Atomic を組み合わせる     |
| **Orchestrations** | 複数の Composite を統合    | morning_routine (今後)        | Composite + Atomic を統合 |

## 📊 Nodes vs Workflows の違い

| 観点                 | Nodes                     | Workflows                      |
| -------------------- | ------------------------- | ------------------------------ |
| **役割**             | グラフの中の 1 ステップ   | 実行可能な完全なグラフ         |
| **インターフェース** | `execute(state) -> state` | `run(input) -> output`         |
| **実行**             | 単独では実行できない      | 単独で実行可能 ✅              |
| **API 公開**         | しない                    | する ✅                        |
| **組み合わせ**       | Workflow に追加される     | 他の Workflow から呼び出される |

詳細は `NODES_VS_WORKFLOWS.md` を参照してください。

## 🚀 使い方

### Atomic Workflow の例

```python
from src.workflows.atomic.chat import ChatWorkflow, ChatInput

# ワークフローを初期化
workflow = ChatWorkflow()

# 実行
result = await workflow.run(
    ChatInput(message="こんにちは", temperature=0.7)
)

print(result.response)  # LLMの応答
```

### Composite Workflow の例

```python
from src.workflows.composite.document_analysis.ppt_summary import PPTSummaryWorkflow, PPTSummaryInput

# ワークフローを初期化
workflow = PPTSummaryWorkflow()

# 実行（内部でAtomicワークフローを組み合わせる）
result = await workflow.run(
    PPTSummaryInput(
        file_path="presentation.pptx",
        summary_style="bullet_points"
    )
)

print(result.summary)  # 生成された要約
```

## 🌐 API エンドポイント

### Atomic Workflows

- `POST /workflows/atomic/chat` - シンプルなチャット
- `POST /workflows/atomic/rag-query` - RAG 検索
- `POST /workflows/atomic/document-extract` - ドキュメント抽出

### Composite Workflows

- `POST /workflows/composite/ppt-summary` - PPT 要約
- `POST /workflows/composite/chain-of-thought` - 段階的推論
- `POST /workflows/composite/reflection` - 自己批判的推論

### 後方互換性エイリアス

- `POST /workflows/simple-chat` → `atomic/chat`
- `POST /workflows/ppt-summary` → `composite/ppt-summary`
- `POST /workflows/rag` → `atomic/rag-query`
- `POST /workflows/chain-of-thought` → `composite/chain-of-thought`
- `POST /workflows/reflection` → `composite/reflection`

## 🔄 依存関係フロー

```
API Endpoint
    ↓
Workflows/Composite（複合ワークフロー）
    ↓ Atomicを組み合わせる
Workflows/Atomic（最小実行単位）
    ↓ Nodesを使う
Nodes（グラフの1ステップ）
    ↓ Servicesを使う
Services（ヘルパー関数）
```

## 💡 設計原則

### 1. 段階的な合成

```
Atomic（単一機能）
    ↓ 組み合わせる
Composite（複合機能）
    ↓ さらに統合
Orchestration（統合機能）
```

### 2. 再利用性の最大化

- Atomic は全てのレイヤーで使える
- Composite も上位レイヤーで使える
- 各ワークフローは独立して実行可能

### 3. 明確な責任分離

- **Atomic**: 単一の明確な機能
- **Composite**: 機能の組み合わせとビジネスロジック
- **Orchestration**: 複雑なビジネスプロセス

### 4. テストしやすさ

- 各レイヤーを独立してテスト
- 下から上へ段階的にテスト
- モックが容易

## 📝 新しいワークフローの追加

### Atomic Workflow を追加する場合

1. `src/workflows/atomic/` に新しいファイルを作成
2. 必要な Node をインポート
3. LangGraph を構築
4. `run()` メソッドを実装

```python
from langgraph.graph import StateGraph, START, END
from src.nodes.base import NodeState
from src.nodes.primitives.xxx.node import XXXNode

class MyAtomicWorkflow:
    def __init__(self):
        self.node = XXXNode()
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(NodeState)
        workflow.add_node("my_node", self.node.execute)
        workflow.add_edge(START, "my_node")
        workflow.add_edge("my_node", END)
        return workflow.compile()

    async def run(self, input_data: MyInput) -> MyOutput:
        # 実装
        pass
```

### Composite Workflow を追加する場合

1. `src/workflows/composite/` の適切なカテゴリに新しいファイルを作成
2. 必要な Atomic Workflows をインポート
3. それらを組み合わせて実装

```python
from src.workflows.atomic.chat import ChatWorkflow
from src.workflows.atomic.rag_query import RAGQueryWorkflow

class MyCompositeWorkflow:
    def __init__(self):
        self.chat = ChatWorkflow()
        self.rag = RAGQueryWorkflow()

    async def run(self, input_data: MyInput) -> MyOutput:
        # Atomicワークフローを組み合わせる
        rag_result = await self.rag.run(...)
        chat_result = await self.chat.run(...)
        return MyOutput(...)
```

## 🎓 参考ドキュメント

- `NODES_VS_WORKFLOWS.md` - Nodes と Workflows の違いの詳細
- `WORKFLOWS_NEW_ARCHITECTURE.md` - アーキテクチャ設計の詳細
- `WORKFLOWS_ANALYSIS.md` - 旧構造の問題分析

## 🔮 今後の拡張

### Phase 1: Atomic Layer ✅

- [x] chat.py
- [x] rag_query.py
- [x] document_extract.py

### Phase 2: Composite Layer ✅

- [x] ppt_summary.py
- [x] chain_of_thought.py
- [x] reflection.py

### Phase 3: Composite Layer（追加予定）

- [ ] todo_management/email_to_todo.py
- [ ] document_analysis/qa_system.py

### Phase 4: Orchestrations Layer（将来）

- [ ] daily_assistant/morning_routine.py
- [ ] research_assistant/deep_research.py

---

この 3 層構造により、ワークフローの段階的な拡張と柔軟な組み合わせが可能になります。
