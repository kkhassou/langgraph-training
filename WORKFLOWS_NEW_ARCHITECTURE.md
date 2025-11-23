# Workflows 新アーキテクチャ設計

## 🎯 設計思想

### コンセプト: 段階的な合成（Progressive Composition）

```
Atomic Workflows（原子的）
    ↓ 組み合わせる
Composite Workflows（複合的）
    ↓ さらに統合
Orchestrated Workflows（統合的）
```

**ポイント**:

1. **最小単位から始める** - 単一機能のワークフロー
2. **組み合わせ可能** - Atomic を組み合わせて Composite を作る
3. **段階的に拡張** - Composite をさらに統合して Orchestration を作る

---

## 📁 提案する新構造

### オプション A: 3 層構造（最も拡張性が高い）

```
src/workflows/
│
├── atomic/                          # 原子的ワークフロー（単一機能）
│   ├── __init__.py
│   ├── chat.py                      # シンプルなチャット
│   ├── rag_query.py                 # RAGクエリ
│   ├── document_extract.py          # ドキュメント抽出
│   ├── email_send.py                # メール送信
│   └── slack_post.py                # Slack投稿
│
├── composite/                       # 複合ワークフロー（組み合わせ）
│   ├── __init__.py
│   │
│   ├── intelligent_chat/            # 高度なチャット
│   │   ├── __init__.py
│   │   ├── chain_of_thought.py     # CoT = chat + reasoning
│   │   └── reflection.py           # Reflection = chat + self-critique
│   │
│   ├── document_analysis/           # ドキュメント分析
│   │   ├── __init__.py
│   │   ├── ppt_summary.py          # PPT要約 = extract + chat
│   │   └── qa_system.py            # Q&A = extract + rag + chat
│   │
│   └── todo_management/             # TODO管理
│       ├── __init__.py
│       └── email_to_todo.py        # メール→TODO = extract + parse + send
│
└── orchestrations/                  # 統合ワークフロー（高度な統合）
    ├── __init__.py
    │
    ├── daily_assistant/             # 日次アシスタント
    │   ├── __init__.py
    │   └── morning_routine.py      # メールチェック + TODO作成 + レポート
    │
    └── research_assistant/          # リサーチアシスタント
        ├── __init__.py
        └── deep_research.py        # RAG + CoT + レポート生成
```

**3 層の役割**:

| 層                 | 役割                       | 例                           | 組み合わせ元              |
| ------------------ | -------------------------- | ---------------------------- | ------------------------- |
| **Atomic**         | 単一機能                   | chat, rag_query              | Nodes 層を使う            |
| **Composite**      | 複数の Atomic を組み合わせ | ppt_summary = extract + chat | Atomic を組み合わせる     |
| **Orchestrations** | 複数の Composite を統合    | morning_routine              | Composite + Atomic を統合 |

---

### オプション B: 2 層構造（シンプル）

```
src/workflows/
│
├── core/                            # コアワークフロー（基本機能）
│   ├── __init__.py
│   ├── chat.py
│   ├── rag_query.py
│   ├── document_extract.py
│   └── ...
│
└── applications/                    # アプリケーション（統合機能）
    ├── __init__.py
    │
    ├── intelligent_chat/
    │   ├── chain_of_thought.py
    │   └── reflection.py
    │
    ├── document_analysis/
    │   ├── ppt_summary.py
    │   └── qa_system.py
    │
    ├── todo_management/
    │   └── email_to_todo.py
    │
    └── daily_assistant/
        └── morning_routine.py
```

**2 層の役割**:

| 層               | 役割                      | 例                           |
| ---------------- | ------------------------- | ---------------------------- |
| **Core**         | 基本的な単一機能          | chat, rag                    |
| **Applications** | Core を組み合わせたアプリ | ppt_summary, morning_routine |

---

## 🎯 推奨: オプション A（3 層構造）

### 理由

1. **段階的な拡張が明確**

   - Atomic → Composite → Orchestrations
   - 各段階で責任が明確

2. **組み合わせの柔軟性**

   - Atomic は Composite で使える
   - Composite は Orchestrations で使える
   - 再利用性が最大化

3. **Nodes 層との整合性**

   ```
   Nodes:     primitives → composites
   Workflows: atomic → composite → orchestrations
   ```

4. **将来の拡張性**
   - 新しい Orchestration を追加しやすい
   - 既存の Composite を再利用できる

---

## 📝 各層の詳細設計

### Atomic Layer（原子的ワークフロー）

**責任**: 単一の明確な機能を提供

**例**: `atomic/chat.py`

```python
from langgraph.graph import StateGraph
from src.nodes.primitives.llm.gemini.node import GeminiNode

class ChatWorkflow:
    """シンプルなチャットワークフロー"""

    def __init__(self):
        self.llm = GeminiNode()
        self.graph = self._build()

    def _build(self):
        workflow = StateGraph(NodeState)
        workflow.add_node("chat", self.llm.execute)
        workflow.set_entry_point("chat")
        workflow.add_edge("chat", END)
        return workflow.compile()

    async def run(self, message: str) -> str:
        """メッセージを送信して応答を取得"""
        state = NodeState()
        state.messages = [message]
        result = await self.graph.ainvoke(state)
        return result.data.get("llm_response")
```

**特徴**:

- 単一のノードまたは単純な連鎖
- 5-50 行程度
- 他のワークフローから呼び出されることを想定

---

### Composite Layer（複合ワークフロー）

**責任**: 複数の Atomic を組み合わせて高度な機能を実現

**例**: `composite/document_analysis/ppt_summary.py`

```python
from src.workflows.atomic.document_extract import DocumentExtractWorkflow
from src.workflows.atomic.chat import ChatWorkflow

class PPTSummaryWorkflow:
    """PPT要約ワークフロー（extract + chat）"""

    def __init__(self):
        self.extractor = DocumentExtractWorkflow()
        self.chat = ChatWorkflow()

    async def run(self, ppt_path: str) -> str:
        """PPTファイルを要約"""
        # Step 1: Extract（Atomicを使う）
        extracted_text = await self.extractor.run(ppt_path)

        # Step 2: Summarize（Atomicを使う）
        prompt = f"以下のプレゼンテーション内容を要約してください:\n\n{extracted_text}"
        summary = await self.chat.run(prompt)

        return summary
```

**特徴**:

- 複数の Atomic を組み合わせる
- 50-200 行程度
- ビジネスロジックを含む

---

### Orchestrations Layer（統合ワークフロー）

**責任**: 複数の Composite を統合して複雑なタスクを実現

**例**: `orchestrations/daily_assistant/morning_routine.py`

```python
from src.workflows.composite.todo_management.email_to_todo import EmailToTodoWorkflow
from src.workflows.composite.document_analysis.ppt_summary import PPTSummaryWorkflow
from src.workflows.atomic.slack_post import SlackPostWorkflow

class MorningRoutineWorkflow:
    """朝のルーティンワークフロー"""

    def __init__(self):
        self.email_to_todo = EmailToTodoWorkflow()
        self.ppt_summary = PPTSummaryWorkflow()
        self.slack = SlackPostWorkflow()

    async def run(self) -> Dict[str, Any]:
        """朝のルーティンを実行"""
        results = {}

        # Step 1: メールからTODO抽出（Compositeを使う）
        todos = await self.email_to_todo.run()
        results["todos"] = todos

        # Step 2: 今日のプレゼン資料を要約（Compositeを使う）
        summary = await self.ppt_summary.run("today_presentation.pptx")
        results["summary"] = summary

        # Step 3: Slackに投稿（Atomicを使う）
        report = self._format_report(todos, summary)
        await self.slack.run(channel="daily-report", message=report)

        return results
```

**特徴**:

- 複数の Composite を統合
- 100-500 行程度
- 複雑なビジネスプロセス

---

## 🔄 依存関係の流れ

```
┌─────────────────────────────────────┐
│   Orchestrations                    │  ← 複雑な統合タスク
│   (morning_routine, research...)    │     (Composite + Atomicを使う)
└──────────────┬──────────────────────┘
               ↓ 使う
┌─────────────────────────────────────┐
│   Composite                         │  ← 高度な機能
│   (ppt_summary, email_to_todo...)   │     (Atomicを組み合わせる)
└──────────────┬──────────────────────┘
               ↓ 使う
┌─────────────────────────────────────┐
│   Atomic                            │  ← 基本機能
│   (chat, rag_query, extract...)     │     (Nodesを使う)
└──────────────┬──────────────────────┘
               ↓ 使う
┌─────────────────────────────────────┐
│   Nodes                             │  ← 単位機能
│   (GeminiNode, RAGNode...)          │
└─────────────────────────────────────┘
```

---

## 📊 全体アーキテクチャ

```
┌─────────────────────────────────────────────────┐
│   Workflows - Orchestrations                    │  ← 統合タスク
│   (複数のCompositeを統合)                       │
└──────────────┬──────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────┐
│   Workflows - Composite                         │  ← 高度な機能
│   (複数のAtomicを組み合わせ)                    │
└──────────────┬──────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────┐
│   Workflows - Atomic                            │  ← 基本機能
│   (単一の明確な機能)                            │
└──────────────┬──────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────┐
│   Nodes - Composites                            │  ← ビジネスロジック
│   (Primitivesを組み合わせ)                      │
└──────────────┬──────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────┐
│   Nodes - Primitives                            │  ← 単位機能
│   (汎用的な技術パターン)                        │
└──────────────┬──────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────┐
│   Services                                      │  ← ヘルパー関数
│   (再利用可能な処理)                            │
└──────────────┬──────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────┐
│   Infrastructure                                │  ← 低レベル実装
│   (Embeddings, Vector Stores...)                │
└─────────────────────────────────────────────────┘
```

---

## 🚀 移行計画

### Phase 1: 既存削除と新構造作成

```bash
# 既存を削除
rm -rf src/workflows/basic src/workflows/patterns

# 新しい構造を作成
mkdir -p src/workflows/{atomic,composite,orchestrations}
mkdir -p src/workflows/composite/{intelligent_chat,document_analysis,todo_management}
mkdir -p src/workflows/orchestrations/{daily_assistant,research_assistant}
```

### Phase 2: Atomic Workflows を作成

最小単位から始める：

1. `atomic/chat.py`
2. `atomic/rag_query.py`
3. `atomic/document_extract.py`

### Phase 3: Composite Workflows を作成

Atomic を組み合わせる：

1. `composite/intelligent_chat/chain_of_thought.py`
2. `composite/document_analysis/ppt_summary.py`
3. `composite/todo_management/email_to_todo.py`

### Phase 4: Orchestrations を作成（将来）

Composite を統合する：

1. `orchestrations/daily_assistant/morning_routine.py`

---

## ✨ メリット

### 1. 段階的な拡張

```python
# Step 1: Atomicを作る
chat = ChatWorkflow()

# Step 2: Compositeを作る（Atomicを組み合わせ）
class CoTWorkflow:
    def __init__(self):
        self.chat = ChatWorkflow()  # Atomicを使う

# Step 3: Orchestrationを作る（Compositeを組み合わせ）
class MorningRoutine:
    def __init__(self):
        self.cot = CoTWorkflow()  # Compositeを使う
```

### 2. 再利用性の最大化

- Atomic は全てのレイヤーで使える
- Composite も上位レイヤーで使える

### 3. テストしやすい

- 各レイヤーを独立してテスト
- 下から上へ段階的にテスト

### 4. 明確な責任分離

- Atomic: 単一機能
- Composite: 機能の組み合わせ
- Orchestrations: 複雑なプロセス

---

---

## ✅ 実装完了

**実装日**: 2025 年 11 月 22 日

### 実装済みのワークフロー

#### Atomic Layer

- ✅ `atomic/chat.py` - シンプルなチャット
- ✅ `atomic/rag_query.py` - RAG 検索
- ✅ `atomic/document_extract.py` - ドキュメント抽出

#### Composite Layer

- ✅ `composite/document_analysis/ppt_summary.py` - PPT 要約
- ✅ `composite/intelligent_chat/chain_of_thought.py` - 段階的推論
- ✅ `composite/intelligent_chat/reflection.py` - 自己批判的推論

### API エンドポイント

#### Atomic Workflows

- `POST /workflows/atomic/chat`
- `POST /workflows/atomic/rag-query`
- `POST /workflows/atomic/document-extract`

#### Composite Workflows

- `POST /workflows/composite/ppt-summary`
- `POST /workflows/composite/chain-of-thought`
- `POST /workflows/composite/reflection`

#### 後方互換性

既存のエンドポイント（`/workflows/simple-chat` など）も引き続き動作します。

---

詳細は `src/workflows/README.md` を参照してください。
