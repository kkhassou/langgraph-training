# MCP (Model Context Protocol) Integration

このディレクトリは、MCP（Model Context Protocol）の実装を含みます。

## 構造

```
src/mcp/
├── servers/          # MCPサーバー実装（独立プロセス）
│   ├── slack/       # Slack MCP サーバー
│   ├── github/      # GitHub MCP サーバー
│   ├── notion/      # Notion MCP サーバー
│   └── google/      # Google サービス群 MCP サーバー
│       ├── gmail/
│       ├── calendar/
│       ├── docs/
│       ├── sheets/
│       ├── slides/
│       └── ...
│
└── clients/         # MCPクライアント実装
    ├── base.py      # 基底クライアントクラス
    ├── factory.py   # クライアントファクトリ
    ├── slack.py     # Slack クライアント
    ├── github.py    # GitHub クライアント
    └── ...          # その他のクライアント
```

## MCP サーバーとクライアントの関係

### MCP サーバー（`servers/`）

- **役割**: 外部サービス（Slack、GitHub 等）の API を MCP プロトコルで公開
- **実行**: 独立したプロセスとして動作（stdio 通信）
- **場所**: `src/mcp/servers/{service}/server.py`
- **例**: `src/mcp/servers/slack/server.py`

### MCP クライアント（`clients/`）

- **役割**: MCP サーバーと通信するためのクライアント実装
- **使用**: LangGraph ノードから呼び出される
- **場所**: `src/mcp/clients/{service}.py`
- **例**: `src/mcp/clients/slack.py`

## データフロー

```
LangGraph ノード
    ↓ (uses)
MCP クライアント (src/mcp/clients/slack.py)
    ↓ (stdio communication)
MCP サーバー (src/mcp/servers/slack/server.py)
    ↓ (API calls)
外部サービス (Slack API)
```

## 使用例

### ノードからクライアントを使用

```python
from src.mcp.clients.slack import SlackMCPService

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

1. **サーバー実装**: `src/mcp/servers/{service}/server.py`
2. **クライアント実装**: `src/mcp/clients/{service}.py`
3. **ノード実装**: `src/nodes/integrations/mcp/{service}.py`
4. **ファクトリに登録**: `src/mcp/clients/factory.py`

## 注意事項

- MCP サーバーは環境変数から認証情報を読み取ります
- クライアントは自動的にサーバープロセスを起動・管理します
- サーバーとの通信は stdio（標準入出力）を使用します
