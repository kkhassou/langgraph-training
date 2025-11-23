# Nodes vs Workflows の違い

## 🤔 重要な質問

> **「workflows/atomic と nodes の違いは何？」**

この質問は核心をついています。明確に区別しましょう。

---

## 📊 比較表

| 観点                   | Nodes                      | Workflows (Atomic 含む)          |
| ---------------------- | -------------------------- | -------------------------------- |
| **役割**               | グラフの中の**1 ステップ** | グラフ全体（**実行可能な単位**） |
| **LangGraph での位置** | ノード（頂点）             | グラフ（ノードの集合）           |
| **インターフェース**   | `execute(state) -> state`  | `run(input) -> output`           |
| **状態管理**           | StateGraph の状態を変換    | 入出力の変換                     |
| **実行単位**           | 単独では実行できない       | 単独で実行可能                   |
| **API 公開**           | しない                     | する                             |
| **組み合わせ**         | Workflow に追加される      | 他の Workflow から呼び出される   |

---

## 🎯 具体例で理解する

### Nodes: グラフの中の 1 ステップ

```python
# src/nodes/primitives/llm/gemini/node.py
class GeminiNode(BaseNode):
    """LangGraphのノード（1ステップ）"""

    async def execute(self, state: NodeState) -> NodeState:
        """状態を受け取り、状態を返す"""
        prompt = state.messages[-1]
        response = await GeminiService.generate(prompt)

        # 状態を更新して返す
        state.messages.append(response)
        state.data["llm_response"] = response
        return state
```

**特徴**:

- `NodeState` を受け取る
- `NodeState` を返す
- **単独では実行できない**（StateGraph に追加する必要がある）
- API エンドポイントとして直接公開しない

---

### Workflows/Atomic: グラフ全体（実行可能）

```python
# src/workflows/atomic/chat.py
class ChatWorkflow:
    """LangGraphのグラフ（実行可能な単位）"""

    def __init__(self):
        self.llm = GeminiNode()  # ← ノードを使う
        self.graph = self._build()

    def _build(self):
        """LangGraphを構築"""
        from langgraph.graph import StateGraph, START, END

        workflow = StateGraph(NodeState)

        # ノードを追加
        workflow.add_node("gemini", self.llm.execute)

        # フローを定義
        workflow.add_edge(START, "gemini")
        workflow.add_edge("gemini", END)

        return workflow.compile()  # ← グラフをコンパイル

    async def run(self, message: str) -> str:
        """シンプルなインターフェース"""
        # 状態を作成
        state = NodeState()
        state.messages = [message]

        # グラフを実行
        result = await self.graph.ainvoke(state)

        # 結果を返す
        return result.data.get("llm_response")
```

**特徴**:

- **LangGraph を内部に持つ**（StateGraph）
- ノードを組み合わせたフロー
- **単独で実行可能**（`run()`メソッド）
- API エンドポイントとして公開される
- シンプルな入出力（`str` → `str`）

---

## 🔄 依存関係と実行フロー

```
┌─────────────────────────────────────┐
│  API Endpoint                       │
│  POST /workflows/chat               │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│  Workflows/Atomic                   │
│  ChatWorkflow.run("Hello")          │
│  ┌───────────────────────────────┐  │
│  │  LangGraph (StateGraph)       │  │
│  │  START → gemini → END         │  │
│  └───────────────────────────────┘  │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│  Nodes                              │
│  GeminiNode.execute(state)          │
│  ↓ 使う                             │
│  Services/GeminiService             │
└─────────────────────────────────────┘
```

---

## 💡 なぜ Atomic Workflow が必要なのか？

### 問題: Node だけでは不十分

```python
# ❌ これは直接実行できない
node = GeminiNode()
result = await node.execute(state)  # stateはどこから？
```

**課題**:

1. `NodeState` を手動で作成する必要がある
2. グラフの構築が必要
3. API として公開しにくい

### 解決: Atomic Workflow

```python
# ✅ これは直接実行できる
workflow = ChatWorkflow()
result = await workflow.run("Hello")  # シンプル！
```

**メリット**:

1. シンプルなインターフェース
2. 状態管理を隠蔽
3. API として公開しやすい
4. 他のワークフローから呼び出しやすい

---

## 📝 使い分けのガイドライン

### Nodes を作るべき場合

✅ **処理の単位が明確**

- 「LLM を呼ぶ」
- 「RAG で検索する」
- 「ドキュメントを解析する」

✅ **再利用可能な処理**

- 複数のワークフローで使われる
- 汎用的な機能

✅ **状態の変換が主**

- `NodeState` を受け取り、変換して返す

**例**:

- `GeminiNode` - LLM 呼び出し
- `RAGNode` - RAG 検索
- `SlackNode` - Slack 投稿

---

### Workflows を作るべき場合

✅ **実行可能な単位**

- API エンドポイントとして公開したい
- 単独で完結したタスク

✅ **フローの定義**

- 複数のノードを組み合わせる
- 条件分岐やループがある

✅ **ユーザー向けインターフェース**

- シンプルな入出力
- `run(input) -> output`

**例**:

- `ChatWorkflow` - チャット実行
- `RAGQueryWorkflow` - RAG 検索実行
- `PPTSummaryWorkflow` - PPT 要約

---

## 🎯 Atomic Workflow の役割

### "Atomic" でも Workflow が必要な理由

**Atomic Workflow** = **最小の実行可能単位**

```python
# Atomic であっても、Workflow として定義する
class ChatWorkflow:
    """単一ノードを使うが、完全なワークフローとして定義"""

    def __init__(self):
        self.llm = GeminiNode()  # ← 単一ノード
        self.graph = self._build()  # ← でもグラフとして構築

    async def run(self, message: str) -> str:
        """API として公開できる」」
        state = NodeState()
        state.messages = [message]
        result = await self.graph.ainvoke(state)
        return result.data["llm_response"]
```

**なぜ？**

1. **API エンドポイント化**

   ```python
   @router.post("/workflows/chat")
   async def chat(message: str):
       workflow = ChatWorkflow()
       return await workflow.run(message)
   ```

2. **他のワークフローから呼び出し**

   ```python
   class PPTSummaryWorkflow:  # ← Composite
       def __init__(self):
           self.chat = ChatWorkflow()  # ← Atomicを使う

       async def run(self, ppt_path):
           text = await self.extract(ppt_path)
           summary = await self.chat.run(f"要約: {text}")
           return summary
   ```

3. **統一されたインターフェース**
   - 全てのワークフローが `run()` メソッドを持つ
   - Atomic も Composite も同じように扱える

---

## 🏗️ 完全なアーキテクチャ

```
┌─────────────────────────────────────────────────┐
│  API Layer                                      │
│  - POST /workflows/chat                         │
│  - POST /workflows/rag-query                    │
│  - POST /workflows/ppt-summary                  │
└──────────────┬──────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────┐
│  Workflows - Composite                          │
│  - PPTSummaryWorkflow (Atomicを組み合わせ)      │
│  - EmailToTodoWorkflow                          │
└──────────────┬──────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────┐
│  Workflows - Atomic                             │  ← 実行可能な最小単位
│  - ChatWorkflow (GeminiNodeを使う)              │
│  - RAGQueryWorkflow (RAGNodeを使う)             │
│  - DocumentExtractWorkflow (PPTNodeを使う)      │
└──────────────┬──────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────┐
│  Nodes                                          │  ← グラフの中のステップ
│  - GeminiNode                                   │
│  - RAGNode                                      │
│  - PPTIngestNode                                │
└──────────────┬──────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────┐
│  Services                                       │  ← ヘルパー関数
│  - GeminiService                                │
│  - RAGService                                   │
└─────────────────────────────────────────────────┘
```

---

## ✨ まとめ

### Nodes

- **役割**: LangGraph の中の 1 ステップ
- **インターフェース**: `execute(state) -> state`
- **実行**: 単独では実行できない（グラフに追加される）
- **例**: `GeminiNode`, `RAGNode`

### Workflows (Atomic 含む)

- **役割**: 実行可能な完全なグラフ
- **インターフェース**: `run(input) -> output`
- **実行**: 単独で実行可能
- **例**: `ChatWorkflow`, `PPTSummaryWorkflow`

### Atomic Workflow の特別な役割

- **最小の実行可能単位**
- 単一ノードを使うかもしれないが、完全なワークフローとして定義
- API として公開される
- 他のワークフローから呼び出される
- **Node と上位レイヤーの橋渡し**

---

この区別で明確になりましたか？

