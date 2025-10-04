# MCP統合拡張ガイド
複数のMCPサーバー（Slack、Notion、Gmailなど）を追加する際の構造と手順

## 1. 追加されるフォルダ・ファイル構造

```
langgraph-training/
│
├── mcp_servers/                        # MCPサーバー実装（各サーバーが独立実行可能）
│   ├── __init__.py
│   ├── shared/                         # 全MCPサーバー共通のユーティリティ
│   │   ├── __init__.py
│   │   ├── utils.py                    # 共通ヘルパー関数
│   │   ├── base_server.py              # MCPサーバーの基底クラス
│   │   └── auth/                       # 認証関連共通処理
│   │       ├── __init__.py
│   │       └── oauth_handler.py
│   │
│   ├── slack/                          # Slack MCP サーバー
│   │   ├── __init__.py
│   │   ├── server.py
│   │   ├── config.json
│   │   ├── requirements.txt
│   │   └── README.md
│   │
│   ├── notion/                         # 【新規】Notion MCP サーバー
│   │   ├── __init__.py
│   │   ├── server.py                   # Notion MCPサーバー実装
│   │   ├── config.json                 # Notion API設定
│   │   ├── requirements.txt            # notion-client等
│   │   └── README.md                   # セットアップ手順
│   │
│   └── gmail/                          # 【新規】Gmail MCP サーバー
│       ├── __init__.py
│       ├── server.py                   # Gmail MCPサーバー実装
│       ├── config.json                 # Gmail API設定
│       ├── credentials.json.example    # OAuth認証情報サンプル
│       ├── requirements.txt            # google-api-python-client等
│       └── README.md
│
├── src/
│   ├── nodes/
│   │   └── integrations/               # 外部統合ノード
│   │       ├── __init__.py
│   │       └── mcp/
│   │           ├── __init__.py
│   │           ├── base.py             # MCP統合の基底クラス
│   │           ├── slack.py            # Slack統合ノード
│   │           ├── notion.py           # 【新規】Notion統合ノード
│   │           └── gmail.py            # 【新規】Gmail統合ノード
│   │
│   ├── services/
│   │   └── mcp/                        # MCP クライアントサービス
│   │       ├── __init__.py
│   │       ├── base.py                 # 基底MCPクライアント
│   │       ├── client_factory.py       # クライアント生成Factory
│   │       ├── slack.py                # Slackクライアント
│   │       ├── notion.py               # 【新規】Notionクライアント
│   │       └── gmail.py                # 【新規】Gmailクライアント
│   │
│   ├── graphs/
│   │   ├── slack_report.py             # 既存: Slack連携ワークフロー
│   │   ├── notion_sync.py              # 【新規】Notion同期ワークフロー
│   │   ├── email_assistant.py          # 【新規】Gmail支援ワークフロー
│   │   └── multi_integration.py        # 【新規】複数MCP統合ワークフロー例
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── graphs.py               # 既存エンドポイント
│   │       └── integrations.py         # 【新規】MCP統合管理API
│   │
│   └── core/
│       ├── config.py                   # MCP設定追加
│       └── mcp_registry.py             # 【新規】MCPサーバー登録管理
│
├── docs/
│   ├── features/
│   │   ├── slack/
│   │   │   └── mcp_server_design.md
│   │   ├── notion/                     # 【新規】
│   │   │   ├── README.md
│   │   │   ├── setup.md
│   │   │   └── use_cases.md
│   │   └── gmail/                      # 【新規】
│   │       ├── README.md
│   │       ├── oauth_setup.md
│   │       └── use_cases.md
│   │
│   └── guides/
│       └── adding_new_mcp_server.md    # 【新規】新規MCPサーバー追加手順
│
├── .env.example                        # 環境変数にMCP設定追加
│
└── docker-compose.yml                  # 各MCPサーバーのサービス定義追加
```

---

## 2. 各層の役割と実装内容

### 2.1 MCPサーバー層（`mcp_servers/`）

各MCPサーバーは独立して実行可能なサービス。

#### **Notion MCP サーバー（`mcp_servers/notion/server.py`）**
```python
# 提供する機能例:
# - ページ作成/更新/削除
# - データベース検索
# - ブロック操作
# - ページ内容取得

Tools:
- create_page
- update_page
- search_database
- get_page_content
- create_database_entry
```

#### **Gmail MCP サーバー（`mcp_servers/gmail/server.py`）**
```python
# 提供する機能例:
# - メール送信
# - メール検索
# - ラベル管理
# - メール読み取り
# - 下書き作成

Tools:
- send_email
- search_emails
- read_email
- create_draft
- add_label
- get_thread
```

---

### 2.2 サービス層（`src/services/mcp/`）

MCPサーバーとの通信を担当するクライアント。

#### **ファイル構成**
- `base.py`: 全MCPクライアントの基底クラス
- `client_factory.py`: クライアント生成Factory
- `slack.py`, `notion.py`, `gmail.py`: 各サービス固有クライアント

#### **Factory パターン実装例**
```python
# src/services/mcp/client_factory.py
class MCPClientFactory:
    @staticmethod
    def create_client(service_type: str):
        if service_type == "slack":
            return SlackMCPClient()
        elif service_type == "notion":
            return NotionMCPClient()
        elif service_type == "gmail":
            return GmailMCPClient()
        else:
            raise ValueError(f"Unknown MCP service: {service_type}")
```

---

### 2.3 ノード層（`src/nodes/integrations/mcp/`）

LangGraphワークフロー内で使用するノード実装。

#### **追加ファイル**
- `notion.py`: Notion操作ノード
- `gmail.py`: Gmail操作ノード

#### **実装例（Notionノード）**
```python
# src/nodes/integrations/mcp/notion.py
class NotionCreatePageNode(BaseMCPNode):
    """Notionページ作成ノード"""

    async def execute(self, state: dict) -> dict:
        client = NotionMCPClient()
        result = await client.call_tool(
            "create_page",
            {
                "parent_id": state["parent_id"],
                "title": state["title"],
                "content": state["content"]
            }
        )
        return {"notion_page_url": result["url"]}
```

---

### 2.4 グラフ層（`src/graphs/`）

複数のMCP統合を組み合わせたワークフロー。

#### **追加ファイル例**

**`notion_sync.py`**: SlackからNotionへの同期
```python
# ワークフロー例:
# 1. Slackメッセージを取得
# 2. LLMで要約・構造化
# 3. Notionデータベースに保存
```

**`email_assistant.py`**: Gmailアシスタント
```python
# ワークフロー例:
# 1. 未読メールを検索
# 2. LLMで要約
# 3. 重要度判定
# 4. 返信案作成
```

**`multi_integration.py`**: 複数サービス連携
```python
# ワークフロー例:
# 1. Gmailで重要メールを検索
# 2. LLMで分析
# 3. Slackに通知
# 4. Notionにタスク作成
```

---

## 3. 新規MCPサーバー追加手順

### Phase 1: MCPサーバー実装

#### ステップ 1.1: ディレクトリ作成
```bash
mkdir -p mcp_servers/notion
mkdir -p mcp_servers/gmail
```

#### ステップ 1.2: サーバー実装
```bash
# Notion MCP サーバー
touch mcp_servers/notion/server.py
touch mcp_servers/notion/config.json
touch mcp_servers/notion/requirements.txt
touch mcp_servers/notion/README.md

# Gmail MCP サーバー
touch mcp_servers/gmail/server.py
touch mcp_servers/gmail/config.json
touch mcp_servers/gmail/credentials.json.example
touch mcp_servers/gmail/requirements.txt
touch mcp_servers/gmail/README.md
```

#### ステップ 1.3: 依存関係定義
```txt
# mcp_servers/notion/requirements.txt
notion-client>=2.0.0
mcp>=0.1.0
python-dotenv>=1.0.0

# mcp_servers/gmail/requirements.txt
google-api-python-client>=2.0.0
google-auth-httplib2>=0.1.0
google-auth-oauthlib>=1.0.0
mcp>=0.1.0
python-dotenv>=1.0.0
```

#### ステップ 1.4: 設定ファイル作成
```json
// mcp_servers/notion/config.json
{
  "notion_api_key": "${NOTION_API_KEY}",
  "default_database_id": "${NOTION_DATABASE_ID}"
}

// mcp_servers/gmail/config.json
{
  "credentials_file": "credentials.json",
  "token_file": "token.json",
  "scopes": [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
  ]
}
```

---

### Phase 2: クライアント実装

#### ステップ 2.1: クライアントファイル作成
```bash
touch src/services/mcp/notion.py
touch src/services/mcp/gmail.py
touch src/services/mcp/client_factory.py
```

#### ステップ 2.2: 基底クラス拡張
`src/services/mcp/base.py`を全MCPクライアントで共通化

#### ステップ 2.3: Factory実装
`src/services/mcp/client_factory.py`でクライアント生成ロジック統一

---

### Phase 3: ノード実装

#### ステップ 3.1: ノードファイル作成
```bash
touch src/nodes/integrations/mcp/notion.py
touch src/nodes/integrations/mcp/gmail.py
```

#### ステップ 3.2: ノードクラス実装
各MCPサービスの機能をLangGraphノードとして実装

---

### Phase 4: グラフ実装

#### ステップ 4.1: ワークフローファイル作成
```bash
touch src/graphs/notion_sync.py
touch src/graphs/email_assistant.py
touch src/graphs/multi_integration.py
```

#### ステップ 4.2: ワークフロー定義
複数のノードを組み合わせたグラフを定義

---

### Phase 5: API・設定整備

#### ステップ 5.1: API エンドポイント追加
```bash
touch src/api/v1/integrations.py
```

#### ステップ 5.2: 環境変数設定
```bash
# .env に追加
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_database_id

GMAIL_CREDENTIALS_FILE=mcp_servers/gmail/credentials.json
GMAIL_TOKEN_FILE=mcp_servers/gmail/token.json
```

#### ステップ 5.3: Docker Compose 更新
```yaml
# docker-compose.yml に追加
services:
  notion-mcp:
    build:
      context: ./mcp_servers/notion
    environment:
      - NOTION_API_KEY=${NOTION_API_KEY}
    ports:
      - "8003:8000"

  gmail-mcp:
    build:
      context: ./mcp_servers/gmail
    volumes:
      - ./mcp_servers/gmail/credentials.json:/app/credentials.json
      - ./mcp_servers/gmail/token.json:/app/token.json
    ports:
      - "8004:8000"
```

---

### Phase 6: テスト・ドキュメント

#### ステップ 6.1: テストファイル作成
```bash
mkdir -p tests/unit/test_services/test_mcp
touch tests/unit/test_services/test_mcp/test_notion_client.py
touch tests/unit/test_services/test_mcp/test_gmail_client.py

mkdir -p tests/integration/test_graphs
touch tests/integration/test_graphs/test_notion_sync.py
touch tests/integration/test_graphs/test_email_assistant.py
```

#### ステップ 6.2: ドキュメント作成
```bash
mkdir -p docs/features/notion
touch docs/features/notion/README.md
touch docs/features/notion/setup.md
touch docs/features/notion/use_cases.md

mkdir -p docs/features/gmail
touch docs/features/gmail/README.md
touch docs/features/gmail/oauth_setup.md
touch docs/features/gmail/use_cases.md

touch docs/guides/adding_new_mcp_server.md
```

---

## 4. 実装チェックリスト

### MCPサーバー
- [ ] `mcp_servers/{service}/server.py` 実装
- [ ] `mcp_servers/{service}/config.json` 設定
- [ ] `mcp_servers/{service}/requirements.txt` 依存関係定義
- [ ] `mcp_servers/{service}/README.md` セットアップ手順
- [ ] ローカルで単独動作確認

### クライアント
- [ ] `src/services/mcp/{service}.py` クライアント実装
- [ ] `src/services/mcp/client_factory.py` にサービス登録
- [ ] エラーハンドリング実装
- [ ] 接続テスト実施

### ノード
- [ ] `src/nodes/integrations/mcp/{service}.py` ノード実装
- [ ] 入出力スキーマ定義
- [ ] 単体テスト作成

### グラフ
- [ ] ワークフロー設計
- [ ] `src/graphs/{workflow_name}.py` 実装
- [ ] 統合テスト作成

### インフラ
- [ ] 環境変数設定（`.env`）
- [ ] Docker設定更新
- [ ] APIエンドポイント追加
- [ ] ドキュメント作成

---

## 5. コード例

### 5.1 Notion MCPクライアント

```python
# src/services/mcp/notion.py
from typing import Dict, Any
from .base import BaseMCPClient

class NotionMCPClient(BaseMCPClient):
    """Notion MCP クライアント"""

    def __init__(self):
        super().__init__(server_url="http://localhost:8003")

    async def create_page(
        self,
        parent_id: str,
        title: str,
        content: str
    ) -> Dict[str, Any]:
        """Notionページを作成"""
        return await self.call_tool(
            "create_page",
            {
                "parent_id": parent_id,
                "title": title,
                "content": content
            }
        )

    async def search_database(
        self,
        database_id: str,
        query: str
    ) -> Dict[str, Any]:
        """Notionデータベースを検索"""
        return await self.call_tool(
            "search_database",
            {
                "database_id": database_id,
                "query": query
            }
        )
```

### 5.2 Gmail MCPクライアント

```python
# src/services/mcp/gmail.py
from typing import Dict, Any, List
from .base import BaseMCPClient

class GmailMCPClient(BaseMCPClient):
    """Gmail MCP クライアント"""

    def __init__(self):
        super().__init__(server_url="http://localhost:8004")

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        """メールを送信"""
        return await self.call_tool(
            "send_email",
            {
                "to": to,
                "subject": subject,
                "body": body
            }
        )

    async def search_emails(
        self,
        query: str,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """メールを検索"""
        return await self.call_tool(
            "search_emails",
            {
                "query": query,
                "max_results": max_results
            }
        )
```

### 5.3 複数MCP統合グラフ

```python
# src/graphs/multi_integration.py
from langgraph.graph import StateGraph
from ..nodes.integrations.mcp.slack import SlackSearchNode
from ..nodes.integrations.mcp.notion import NotionCreatePageNode
from ..nodes.integrations.mcp.gmail import GmailSendNode

class MultiIntegrationWorkflow:
    """複数MCP統合ワークフロー

    フロー:
    1. Slackメッセージ検索
    2. Notionページ作成
    3. Gmail通知送信
    """

    def __init__(self):
        self.graph = StateGraph(dict)
        self._build_graph()

    def _build_graph(self):
        # ノード追加
        self.graph.add_node("search_slack", SlackSearchNode())
        self.graph.add_node("create_notion", NotionCreatePageNode())
        self.graph.add_node("send_email", GmailSendNode())

        # エッジ定義
        self.graph.add_edge("search_slack", "create_notion")
        self.graph.add_edge("create_notion", "send_email")

        # エントリーポイント
        self.graph.set_entry_point("search_slack")
        self.graph.set_finish_point("send_email")

    def compile(self):
        return self.graph.compile()
```

---

## 6. まとめ

### 追加されるファイル数（1サービスあたり）
- MCPサーバー: 4ファイル
- クライアント: 1ファイル
- ノード: 1ファイル
- グラフ: 1〜3ファイル（ユースケース次第）
- テスト: 2〜4ファイル
- ドキュメント: 3〜5ファイル

**合計: 約12〜20ファイル/サービス**

### スケーラビリティ
この構造により:
- 新規MCPサーバーの追加が容易
- 各サービスが独立して開発・テスト可能
- Factoryパターンで依存関係管理が簡潔
- ワークフローの組み合わせが柔軟

### 推奨される順序
1. **Notion追加**: Slackと類似のシンプルなAPI
2. **Gmail追加**: OAuth認証の学習
3. **その他**: GitHub, Google Drive, Trello等

各サービス追加時は、このガイドのPhase 1〜6を順に実施してください。
