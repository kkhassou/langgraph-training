# フォルダ構造移行計画書

## 重要な注意事項
- **Slack MCPを壊さない**: インポートパスの変更は慎重に行う
- **ファイル内容は基本的に変更しない**: フォルダ移動とインポートパス修正のみ
- **段階的に実施**: 各フェーズ後に動作確認

## 現在の依存関係マップ（Slack MCP関連）

```
app/main.py
  ↓ imports
app/api/routes_nodes.py
  ↓ imports
app/nodes/mcp_integrations/slack_mcp_node.py
  ↓ imports
app/services/mcp_services/slack_mcp_client.py
  ↓ imports
app/services/mcp_services/base_mcp_client.py
  ↓ uses
app/mcp_servers/slack/server.py (実際のMCPサーバー)
```

## 移行後の構造

```
app/ → src/
  ├── api/ → src/api/v1/
  ├── nodes/mcp_integrations/ → src/nodes/integrations/mcp/
  ├── services/mcp_services/ → src/services/mcp/
  ├── mcp_servers/ → mcp_servers/ (変更なし・ルート直下)
```

## Phase 1: app/ を src/ にリネーム

### 手順
1. `app/` ディレクトリを `src/` にリネーム
2. `main.py` のインポートパス修正
3. Dockerfile、docker-compose.yml の修正
4. requirements.txt の確認（パス依存なし）

### 影響を受けるファイル
- `app/main.py` → `src/main.py`
  - 自身のインポート: `app.core.config` → `src.core.config`
  - 自身のインポート: `app.api` → `src.api`

- `Dockerfile` (存在する場合)
  - COPY文の修正: `app/` → `src/`

- `docker-compose.yml`
  - volume/pathの修正: `./app` → `./src`

### 動作確認
```bash
# インポートエラーがないか確認
python -c "from src.main import app; print('OK')"

# サーバー起動確認
uvicorn src.main:app --reload
```

---

## Phase 2: src/core/ の拡充

### 新規ファイル作成（内容は最小限）

```bash
touch src/core/exceptions.py
touch src/core/logging.py
touch src/core/constants.py
```

### `src/core/exceptions.py`
```python
"""カスタム例外定義"""

class LangGraphBaseException(Exception):
    """基底例外クラス"""
    pass

class NodeExecutionError(LangGraphBaseException):
    """ノード実行エラー"""
    pass

class MCPError(LangGraphBaseException):
    """MCP関連エラー"""
    pass
```

### `src/core/constants.py`
```python
"""定数定義"""

DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1000
DEFAULT_COLLECTION_NAME = "default_collection"
DEFAULT_TOP_K = 5
```

### `src/core/logging.py`
```python
"""ログ設定"""
import logging
import sys

def setup_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
```

### 影響なし
既存のファイルは変更しない

---

## Phase 3: src/domain/ 層を作成

### ディレクトリ構造
```bash
mkdir -p src/domain/models
mkdir -p src/domain/schemas
touch src/domain/__init__.py
touch src/domain/models/__init__.py
touch src/domain/schemas/__init__.py
```

### 将来的な配置（現時点では作成のみ）
- `src/domain/models/`: ビジネスロジックとデータモデル
- `src/domain/schemas/`: Pydanticスキーマ（API入出力）

### 影響なし
新規作成のみ、既存コードは変更しない

---

## Phase 4: src/nodes/ を機能別に再構成

### 現在の構造
```
src/nodes/
  ├── base_node.py
  ├── llm_gemini.py
  ├── ppt_ingest.py
  ├── mcp_integrations/
  │   ├── __init__.py
  │   ├── mcp_base.py
  │   └── slack_mcp_node.py
  └── rag/
      └── (複数ファイル)
```

### 移行後の構造
```
src/nodes/
  ├── __init__.py
  ├── base.py (base_node.py からリネーム)
  ├── llm/
  │   ├── __init__.py
  │   ├── base_llm.py (新規・将来用)
  │   └── gemini.py (llm_gemini.py から移動)
  ├── document/
  │   ├── __init__.py
  │   └── ppt_ingest.py (移動)
  ├── integrations/
  │   ├── __init__.py
  │   └── mcp/
  │       ├── __init__.py
  │       ├── base.py (mcp_base.py から移動)
  │       └── slack.py (slack_mcp_node.py から移動)
  └── rag/
      └── (変更なし)
```

### 手順

#### ステップ 4.1: llm/ サブディレクトリ作成
```bash
mkdir -p src/nodes/llm
touch src/nodes/llm/__init__.py
mv src/nodes/llm_gemini.py src/nodes/llm/gemini.py
```

#### ステップ 4.2: インポートパス修正
`src/nodes/llm/gemini.py`:
```python
# 変更前
from app.nodes.base_node import BaseNode

# 変更後
from src.nodes.base import BaseNode
```

`src/api/routes_nodes.py`:
```python
# 変更前
from app.nodes.llm_gemini import GeminiInput, gemini_node_handler

# 変更後
from src.nodes.llm.gemini import GeminiInput, gemini_node_handler
```

#### ステップ 4.3: document/ サブディレクトリ作成
```bash
mkdir -p src/nodes/document
touch src/nodes/document/__init__.py
mv src/nodes/ppt_ingest.py src/nodes/document/ppt_ingest.py
```

#### ステップ 4.4: integrations/mcp/ サブディレクトリ再編成
```bash
mkdir -p src/nodes/integrations/mcp
touch src/nodes/integrations/__init__.py
touch src/nodes/integrations/mcp/__init__.py
mv src/nodes/mcp_integrations/mcp_base.py src/nodes/integrations/mcp/base.py
mv src/nodes/mcp_integrations/slack_mcp_node.py src/nodes/integrations/mcp/slack.py
rm -rf src/nodes/mcp_integrations
```

#### ステップ 4.5: **重要** Slack MCPノードのインポートパス修正

`src/nodes/integrations/mcp/slack.py`:
```python
# 変更前
from app.nodes.base_node import BaseNode, NodeState, NodeInput, NodeOutput
from app.services.mcp_services.slack_mcp_client import SlackMCPService

# 変更後
from src.nodes.base import BaseNode, NodeState, NodeInput, NodeOutput
from src.services.mcp.slack_mcp_client import SlackMCPService
```

`src/api/routes_nodes.py`:
```python
# 変更前
from app.nodes.mcp_integrations.slack_mcp_node import SlackMCPInput, slack_mcp_node_handler

# 変更後
from src.nodes.integrations.mcp.slack import SlackMCPInput, slack_mcp_node_handler
```

#### ステップ 4.6: base_node.py のリネーム
```bash
mv src/nodes/base_node.py src/nodes/base.py
```

すべての base_node からのインポートを修正:
```bash
# src/nodes/ 配下の全ファイルで
from app.nodes.base_node → from src.nodes.base
```

### 動作確認
```bash
# Slack MCPノードのインポート確認
python -c "from src.nodes.integrations.mcp.slack import SlackMCPNode; print('OK')"

# API起動確認
uvicorn src.main:app --reload
```

---

## Phase 5: src/services/mcp/ にFactoryパターン導入

### 現在の構造
```
src/services/
  └── mcp_services/
      ├── __init__.py
      ├── base_mcp_client.py
      └── slack_mcp_client.py
```

### 移行後の構造
```
src/services/
  └── mcp/
      ├── __init__.py
      ├── base.py (base_mcp_client.py からリネーム)
      ├── slack.py (slack_mcp_client.py からリネーム)
      └── factory.py (新規)
```

### 手順

#### ステップ 5.1: ディレクトリリネーム
```bash
mv src/services/mcp_services src/services/mcp
```

#### ステップ 5.2: ファイルリネーム
```bash
mv src/services/mcp/base_mcp_client.py src/services/mcp/base.py
mv src/services/mcp/slack_mcp_client.py src/services/mcp/slack.py
```

#### ステップ 5.3: **重要** インポートパス修正

`src/services/mcp/slack.py`:
```python
# 変更前
from .base_mcp_client import BaseMCPClient, MCPConnectionError, MCPToolError

# 変更後
from .base import BaseMCPClient, MCPConnectionError, MCPToolError
```

**重要**: MCPサーバーパス解決の修正
```python
# src/services/mcp/slack.py 内
# 変更前
server_script = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "mcp_servers", "slack", "server.py"
)

# 変更後（src/ に移動したため、パス調整）
server_script = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "mcp_servers", "slack", "server.py"
)
```

#### ステップ 5.4: Factoryパターン実装

`src/services/mcp/factory.py`:
```python
"""MCP Client Factory"""
from typing import Dict, Any
from .base import BaseMCPClient
from .slack import SlackMCPClient

class MCPClientFactory:
    """MCPクライアント生成Factory"""

    _clients: Dict[str, type] = {
        "slack": SlackMCPClient,
    }

    @classmethod
    def create_client(cls, service_type: str, **kwargs) -> BaseMCPClient:
        """MCPクライアント生成

        Args:
            service_type: サービスタイプ（slack, notion, gmail等）
            **kwargs: クライアント固有の設定

        Returns:
            BaseMCPClient: MCPクライアントインスタンス
        """
        client_class = cls._clients.get(service_type)
        if not client_class:
            raise ValueError(f"Unknown MCP service type: {service_type}")

        return client_class(**kwargs)

    @classmethod
    def register_client(cls, service_type: str, client_class: type):
        """新規MCPクライアントを登録"""
        cls._clients[service_type] = client_class
```

#### ステップ 5.5: ノード側のインポートパス修正

`src/nodes/integrations/mcp/slack.py`:
```python
# 変更前
from app.services.mcp_services.slack_mcp_client import SlackMCPService

# 変更後
from src.services.mcp.slack import SlackMCPService
```

### 動作確認
```bash
# インポート確認
python -c "from src.services.mcp.slack import SlackMCPClient; print('OK')"
python -c "from src.services.mcp.factory import MCPClientFactory; print('OK')"

# Factory動作確認
python -c "from src.services.mcp.factory import MCPClientFactory; client = MCPClientFactory.create_client('slack'); print('Factory OK')"
```

---

## Phase 6: src/api/ の再構成

### 現在の構造
```
src/api/
  ├── routes_nodes.py
  ├── routes_graphs.py
  └── routes_nodes_minimal.py
```

### 移行後の構造
```
src/api/
  ├── __init__.py
  ├── dependencies.py (新規・将来用)
  └── v1/
      ├── __init__.py
      ├── nodes.py (routes_nodes.py からリネーム)
      ├── graphs.py (routes_graphs.py からリネーム)
      └── minimal.py (routes_nodes_minimal.py からリネーム)
```

### 手順

#### ステップ 6.1: v1/ ディレクトリ作成
```bash
mkdir -p src/api/v1
touch src/api/v1/__init__.py
```

#### ステップ 6.2: ファイル移動・リネーム
```bash
mv src/api/routes_nodes.py src/api/v1/nodes.py
mv src/api/routes_graphs.py src/api/v1/graphs.py
mv src/api/routes_nodes_minimal.py src/api/v1/minimal.py
```

#### ステップ 6.3: main.py のインポート修正

`src/main.py`:
```python
# 変更前
from app.api import routes_nodes, routes_graphs

# 変更後
from src.api.v1 import nodes, graphs

# ルーター登録も修正
# 変更前
app.include_router(routes_nodes.router)
app.include_router(routes_graphs.router)

# 変更後
app.include_router(nodes.router)
app.include_router(graphs.router)
```

#### ステップ 6.4: API v1ファイル内のインポート修正

`src/api/v1/nodes.py`:
```python
# すべてのインポートを app. → src. に変更
from src.nodes.llm.gemini import GeminiInput, gemini_node_handler
from src.nodes.document.ppt_ingest import ppt_ingest_handler
from src.nodes.integrations.mcp.slack import SlackMCPInput, slack_mcp_node_handler
from src.nodes.rag.rag_node import RAGInput, rag_node_handler
# ... 等々
```

`src/api/v1/graphs.py`:
```python
# すべてのインポートを app. → src. に変更
```

### 動作確認
```bash
uvicorn src.main:app --reload
# http://localhost:8000/docs でAPI確認
# POST /nodes/slack-mcp をテスト
```

---

## Phase 7: tests/ 構造の改善

### 現在の構造
```
tests/
  ├── test_api/
  ├── test_graphs/
  └── test_nodes/
```

### 移行後の構造
```
tests/
  ├── __init__.py
  ├── conftest.py (新規)
  ├── unit/
  │   ├── __init__.py
  │   ├── test_nodes/
  │   ├── test_services/
  │   └── test_infrastructure/
  ├── integration/
  │   ├── __init__.py
  │   ├── test_graphs/
  │   └── test_api/
  └── fixtures/
      ├── __init__.py
      └── documents/
```

### 手順
```bash
mkdir -p tests/unit tests/integration tests/fixtures
touch tests/__init__.py tests/conftest.py
touch tests/unit/__init__.py tests/integration/__init__.py tests/fixtures/__init__.py

# 既存テストを移動
mv tests/test_api tests/integration/test_api
mv tests/test_graphs tests/integration/test_graphs
mv tests/test_nodes tests/unit/test_nodes
```

### `tests/conftest.py`
```python
"""pytest共通設定"""
import pytest
import sys
from pathlib import Path

# src/ をPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

---

## Phase 8: docs/ の再編成

### 移行後の構造
```
docs/
  ├── README.md
  ├── architecture/
  │   ├── overview.md
  │   ├── diagrams/ (既存)
  │   └── mcp_integration.md
  ├── guides/
  │   ├── workshop_guide.md (移動)
  │   ├── quick_reference.md (移動)
  │   └── file_structure_guide.md (移動)
  └── features/
      ├── rag/ (既存)
      └── slack/
          └── mcp_server_design.md (移動)
```

### 手順
```bash
mkdir -p docs/architecture docs/guides docs/features/slack
mv docs/workshop_guide.md docs/guides/
mv docs/quick_reference.md docs/guides/
mv docs/file_structure_guide.md docs/guides/
mv docs/slack_mcp_server_design.md docs/features/slack/
mv docs/diagrams docs/architecture/diagrams
```

---

## Phase 9: docker/ とdata/ の整理

### docker/ ディレクトリ作成
```bash
mkdir -p docker
mv Dockerfile docker/
mv docker-compose.yml docker/
```

`docker/Dockerfile` の修正:
```dockerfile
# COPY app/ . → COPY src/ .
COPY src/ ./src/
```

`docker/docker-compose.yml` の修正:
```yaml
# volumes:
#   - ./app:/app/app
# ↓
volumes:
  - ../src:/app/src
```

### data/ ディレクトリ作成
```bash
mkdir -p data/uploads data/vector_db data/cache
touch data/.gitkeep
```

`.gitignore` に追加:
```
data/uploads/*
data/vector_db/*
data/cache/*
!data/.gitkeep
```

---

## Phase 10: 動作確認（特にSlack MCP）

### チェックリスト

#### 1. インポート確認
```bash
python -c "from src.main import app; print('Main OK')"
python -c "from src.nodes.integrations.mcp.slack import SlackMCPNode; print('Node OK')"
python -c "from src.services.mcp.slack import SlackMCPService; print('Service OK')"
```

#### 2. MCPサーバーパス確認
```bash
python -c "
from src.services.mcp.slack import SlackMCPClient
import os
client = SlackMCPClient()
# server_scriptパスが正しいか出力
print('MCP server path exists:', os.path.exists(client.server_config.get('script_path', '')))
"
```

#### 3. API起動確認
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 4. Slack MCP動作確認
```bash
# http://localhost:8000/docs にアクセス
# POST /nodes/slack-mcp で get_channels をテスト
curl -X POST http://localhost:8000/nodes/slack-mcp \
  -H "Content-Type: application/json" \
  -d '{"action": "get_channels"}'
```

#### 5. エラーログ確認
- MCPサーバー接続エラーがないか
- インポートエラーがないか
- パス解決エラーがないか

---

## ロールバック手順

各Phase失敗時:

### Phase 1失敗時
```bash
mv src app
git checkout Dockerfile docker-compose.yml
```

### Phase 4失敗時（ノード再構成）
```bash
git checkout src/nodes/
git checkout src/api/
```

### Phase 5失敗時（services/mcp）
```bash
mv src/services/mcp src/services/mcp_services
mv src/services/mcp_services/base.py src/services/mcp_services/base_mcp_client.py
mv src/services/mcp_services/slack.py src/services/mcp_services/slack_mcp_client.py
```

---

## 完了後の最終構造

```
langgraph-training/
├── src/                    # app/ からリネーム
│   ├── api/v1/             # バージョン管理
│   ├── core/               # 拡充済み
│   ├── domain/             # 新規作成
│   ├── nodes/              # 機能別整理済み
│   │   ├── llm/
│   │   ├── document/
│   │   ├── integrations/mcp/
│   │   └── rag/
│   ├── services/mcp/       # Factory導入済み
│   └── main.py
├── mcp_servers/            # 変更なし
├── tests/                  # unit/integration分離
├── docs/                   # 再編成済み
├── docker/                 # 新規
├── data/                   # 新規
└── scripts/                # 変更なし
```
