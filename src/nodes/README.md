# Nodes - LangGraph ノード実装

このディレクトリは、LangGraph で使用される各種ノードの実装を含みます。

## 現在の構造（整理前）

```
src/nodes/
├── base.py              # 基底クラス
├── llm/                 # LLM関連
│   └── gemini.py
├── document/            # ドキュメント処理
│   └── ppt_ingest.py
├── integrations/        # 外部統合
│   └── mcp/            # MCP統合（12個のファイル）
│       ├── slack.py
│       ├── github.py
│       └── ...
├── rag/                 # RAG関連（4個のファイル）
├── todo/                # TODO処理（3個のファイル）
└── utils/

問題点：
- integrations/mcp/ に全てのサービスが入っている（拡張性が低い）
- MCPの構造（src/mcp/slack/、src/mcp/github/）と統一されていない
- 新しいサービスを追加すると、フォルダがどんどん大きくなる
```

## 提案する新しい構造（拡張性重視）

```
src/nodes/
├── base.py              # 基底クラス
│
├── llm/                 # LLM関連
│   ├── base.py         # LLM基底クラス
│   └── gemini/
│       ├── __init__.py
│       └── node.py     # GeminiNode実装
│
├── document/            # ドキュメント処理
│   ├── base.py         # ドキュメント基底クラス
│   └── ppt/
│       ├── __init__.py
│       └── node.py     # PPTIngestNode実装
│
├── integrations/        # 外部サービス統合
│   ├── base.py         # 統合基底クラス
│   │
│   ├── slack/          # Slack統合
│   │   ├── __init__.py
│   │   └── node.py
│   │
│   ├── github/         # GitHub統合
│   │   ├── __init__.py
│   │   └── node.py
│   │
│   ├── notion/         # Notion統合
│   │   ├── __init__.py
│   │   └── node.py
│   │
│   └── google/         # Google サービス群
│       ├── gmail/
│       │   ├── __init__.py
│       │   └── node.py
│       ├── calendar/
│       │   ├── __init__.py
│       │   └── node.py
│       └── ...
│
├── rag/                 # RAG関連
│   ├── base.py         # RAG基底クラス
│   ├── simple/
│   │   ├── __init__.py
│   │   └── node.py
│   ├── advanced/
│   │   ├── __init__.py
│   │   └── node.py
│   ├── search/
│   │   ├── __init__.py
│   │   └── node.py
│   └── ingest/
│       ├── __init__.py
│       └── node.py
│
├── todo/                # TODO処理
│   ├── base.py         # TODO基底クラス
│   ├── parser/
│   │   ├── __init__.py
│   │   └── node.py
│   ├── advisor/
│   │   ├── __init__.py
│   │   └── node.py
│   └── composer/
│       ├── __init__.py
│       └── node.py
│
└── utils/               # ユーティリティ
    └── array_splitter.py
```

## 新構造の利点

### 1. 拡張性が高い

- 各サービスが独立したフォルダ
- 新しいサービスの追加が容易
- サービスごとに複数のファイルを追加可能

### 2. MCP と構造が統一

```
src/mcp/slack/client.py  ← MCP クライアント
src/nodes/integrations/slack/node.py  ← ノード実装
```

### 3. 保守性が高い

- サービス単位で管理
- 関連ファイルがまとまっている
- テストファイルも同じフォルダに配置可能

### 4. 可読性が向上

- フォルダ構造で機能が明確
- ファイル名が統一（全て `node.py`）

## 命名規則

### ファイル構造

```
src/nodes/{category}/{service}/
├── __init__.py      # エクスポート（Node, Input, Outputなど）
├── node.py          # ノード実装
├── schemas.py       # 入出力スキーマ（必要な場合）
└── utils.py         # ヘルパー関数（必要な場合）
```

### クラス名

```python
# node.py
class {Service}Node(BaseNode):
    """メインノードクラス"""
    pass

class {Service}Input(NodeInput):
    """入力スキーマ"""
    pass

class {Service}Output(NodeOutput):
    """出力スキーマ"""
    pass
```

### **init**.py でのエクスポート

```python
from .node import SlackNode, SlackInput, SlackOutput

__all__ = ["SlackNode", "SlackInput", "SlackOutput"]
```

## 使用例

### 既存のインポート（整理前）

```python
from src.nodes.integrations.mcp.slack import SlackMCPNode, SlackMCPInput
from src.nodes.llm.gemini import GeminiNode
```

### 新しいインポート（整理後）

```python
from src.nodes.integrations.slack import SlackNode, SlackInput
from src.nodes.llm.gemini import GeminiNode
```

## 移行計画

1. **Phase 1**: 新しいフォルダ構造を作成
2. **Phase 2**: ファイルを新しい場所に移動・リネーム
3. **Phase 3**: インポートパスを更新
4. **Phase 4**: 古いファイルを削除
5. **Phase 5**: ドキュメント更新

## 新しいノードの追加方法

```bash
# 1. サービスフォルダを作成
mkdir -p src/nodes/integrations/{service}

# 2. 必要なファイルを作成
touch src/nodes/integrations/{service}/__init__.py
touch src/nodes/integrations/{service}/node.py

# 3. node.py を実装
# 4. __init__.py でエクスポート
# 5. API routes に追加
```

この構造により、新しいサービスの追加やメンテナンスが格段に容易になります。
