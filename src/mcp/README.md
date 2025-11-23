# MCP (Model Context Protocol) Integration

このディレクトリは、MCP（Model Context Protocol）の実装を含みます。

## 構造

```
src/mcp/
├── base.py              # 基底クライアントクラス
├── factory.py           # クライアントファクトリ
│
├── slack/               # Slack MCP 実装
│   ├── client.py       # クライアント実装
│   └── server.py       # サーバー実装（独立プロセス）
│
├── github/              # GitHub MCP 実装
│   ├── client.py
│   └── server.py
│
├── notion/              # Notion MCP 実装
│   ├── client.py
│   └── server.py
│
└── google/              # Google サービス群 MCP 実装
    ├── gmail/
    │   ├── client.py
    │   └── server.py
    ├── calendar/
    │   ├── client.py
    │   └── server.py
    ├── docs/
    │   ├── client.py
    │   └── server.py
    ├── sheets/
    │   ├── client.py
    │   └── server.py
    ├── slides/
    │   ├── client.py
    │   └── server.py
    ├── forms/
    │   ├── client.py
    │   └── server.py
    ├── keep/
    │   ├── client.py
    │   └── server.py
    ├── apps_script/
    │   ├── client.py
    │   └── server.py
    └── vertex_ai/
        ├── client.py
        └── server.py
```

## MCP サーバーとクライアントの関係

各サービスフォルダには 2 つのファイルがあります：

### クライアント（`client.py`）

- **役割**: MCP サーバーと通信するためのクライアント実装
- **使用**: LangGraph ノードから呼び出される
- **場所**: `src/mcp/{service}/client.py`
- **例**: `src/mcp/slack/client.py`
- **クラス**: `{Service}MCPClient`, `{Service}MCPService`

### サーバー（`server.py`）

- **役割**: 外部サービス（Slack、GitHub 等）の API を MCP プロトコルで公開
- **実行**: 独立したプロセスとして動作（stdio 通信）
- **場所**: `src/mcp/{service}/server.py`
- **例**: `src/mcp/slack/server.py`

## データフロー

```
LangGraph ノード
    ↓ (uses)
MCP クライアント (src/mcp/slack/client.py)
    ↓ (stdio communication)
MCP サーバー (src/mcp/slack/server.py)
    ↓ (API calls)
外部サービス (Slack API)
```

## 使用例

### ノードからクライアントを使用

```python
from src.mcp.slack.client import SlackMCPService

# クライアントのインスタンス化
service = SlackMCPService()

# サーバーへ接続
await service.connect()

# ツールの実行
result = await service.call_tool("get_channels", {})

# 切断
await service.disconnect()
```

## 新しい MCP 統合の追加

1. **サービスフォルダを作成**: `src/mcp/{service}/`
2. **クライアント実装**: `src/mcp/{service}/client.py`
3. **サーバー実装**: `src/mcp/{service}/server.py`
4. **ノード実装**: `src/nodes/integrations/mcp/{service}.py`
5. **ファクトリに登録**: `src/mcp/factory.py`

## インポート方法

```python
# クライアントのインポート
from src.mcp.slack.client import SlackMCPClient, SlackMCPService
from src.mcp.github.client import GitHubMCPClient, GitHubMCPService
from src.mcp.google.gmail.client import GmailMCPClient, GmailMCPService

# ファクトリからの取得
from src.mcp.factory import MCPClientFactory
client = MCPClientFactory.create_client("slack")
```

## 構造の利点

✅ **一箇所にまとまっている**: 各サービスのクライアントとサーバーが同じフォルダ内
✅ **理解しやすい**: サービス単位でフォルダが分かれている
✅ **保守性が高い**: 関連ファイルが近くにある
✅ **スケーラブル**: 新しいサービスの追加が容易

## 注意事項

- MCP サーバーは環境変数から認証情報を読み取ります
- クライアントは自動的にサーバープロセスを起動・管理します
- サーバーとの通信は stdio（標準入出力）を使用します
- クライアントとサーバーは同じフォルダ内にあるため、パス参照が簡単です
