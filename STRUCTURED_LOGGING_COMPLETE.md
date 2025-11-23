# 構造化ロギングの実装完了レポート ✅

## 📋 概要

完全な構造化ロギングシステムを実装しました。JSON形式でのログ出力、コンテキスト変数の追跡、ワークフロー/ノード/API呼び出しの自動ロギングを含みます。

## 🎯 実装内容

### 1. StructuredLoggerクラスの実装

**ファイル**: `src/core/logging_config.py`

以下の機能を持つ高レベルロギングクラスを実装：

```python
from src.core.logging_config import get_structured_logger

logger = get_structured_logger(__name__)

# ワークフロー開始
logger.workflow_start("ChatWorkflow", {"message_length": 150})

# ノード実行
logger.node_execute("llm_node", "LLMNode", 0.523, success=True)

# プロバイダー呼び出し
logger.provider_call("GeminiProvider", "generate", 0.823)

# API リクエスト
logger.api_request("POST", "/workflows/chat", 200, 1.234)

# ワークフロー完了
logger.workflow_end("ChatWorkflow", 1.234, success=True)
```

#### 主要メソッド：
- `workflow_start()`: ワークフロー開始ログ
- `workflow_end()`: ワークフロー完了ログ（成功/失敗）
- `node_execute()`: ノード実行ログ
- `provider_call()`: プロバイダー呼び出しログ
- `api_request()`: APIリクエストログ
- `info()`, `warning()`, `error()`, `debug()`: 標準ログレベル

### 2. コンテキスト変数の追加

すべてのログに自動的に含まれるコンテキスト情報：

```python
from src.core.logging_config import (
    set_request_id,
    set_user_id,
    set_workflow_id,
    set_node_id
)

# リクエストID（APIレスポンスヘッダーにも含まれる）
request_id = set_request_id()  # 自動生成
set_request_id("custom-req-123")  # カスタムID

# ユーザーID（認証システムから取得）
set_user_id("user-456")

# ワークフローID（ワークフロー実行時に自動設定）
workflow_id = set_workflow_id()

# ノードID（ノード実行時に自動設定）
set_node_id("llm_node")
```

#### コンテキスト変数：
- `request_id_var`: HTTPリクエストの追跡
- `user_id_var`: ユーザーの追跡
- `workflow_id_var`: ワークフロー実行の追跡
- `node_id_var`: ノード実行の追跡

### 3. ワークフローへのロギング統合

**実装ファイル**:
- `src/workflows/atomic/chat.py`
- `src/workflows/composite/intelligent_chat/chain_of_thought.py`

```python
async def run(self, input_data: ChatInput) -> ChatOutput:
    # ワークフローIDを設定
    workflow_id = set_workflow_id()
    start_time = time.time()
    
    try:
        # 構造化ロギング: ワークフロー開始
        structured_logger.workflow_start(
            "ChatWorkflow",
            {"message_length": len(input_data.message)}
        )
        
        # ... ワークフロー実行 ...
        
        # 構造化ロギング: ワークフロー完了
        duration = time.time() - start_time
        structured_logger.workflow_end("ChatWorkflow", duration, success=True)
        
        return result
        
    except Exception as e:
        duration = time.time() - start_time
        structured_logger.workflow_end(
            "ChatWorkflow",
            duration,
            success=False,
            error=str(e)
        )
        raise
    finally:
        clear_workflow_id()
```

#### 統合内容：
- ワークフロー開始/完了の自動ログ
- 実行時間の自動計測
- エラー時の詳細ログ
- ワークフローIDの自動管理

### 4. ノードへのロギング統合

**実装ファイル**: `src/nodes/primitives/llm/gemini/node.py`

```python
async def execute(self, state: NodeState) -> NodeState:
    # ノードIDを設定
    set_node_id(self.name)
    start_time = time.time()
    
    try:
        # プロバイダー呼び出し
        provider_start_time = time.time()
        response_text = await self.provider.generate(...)
        provider_duration = time.time() - provider_start_time
        
        # 構造化ロギング: プロバイダー呼び出し
        structured_logger.provider_call(
            self.provider.__class__.__name__,
            "generate",
            provider_duration,
            success=True
        )
        
        # 構造化ロギング: ノード実行完了
        duration = time.time() - start_time
        structured_logger.node_execute(
            self.name,
            self.__class__.__name__,
            duration,
            success=True
        )
        
        return state
        
    except Exception as e:
        duration = time.time() - start_time
        structured_logger.node_execute(
            self.name,
            self.__class__.__name__,
            duration,
            success=False
        )
        raise
    finally:
        clear_node_id()
```

#### 統合内容：
- ノード実行の自動ログ
- プロバイダー呼び出しの自動ログ
- 実行時間の自動計測
- エラー時の詳細ログ
- ノードIDの自動管理

### 5. APIエンドポイントへのロギング追加

**実装ファイル**: `src/main.py`

FastAPIミドルウェアを実装：

```python
class LoggingMiddleware(BaseHTTPMiddleware):
    """構造化ロギングミドルウェア"""
    
    async def dispatch(self, request: Request, call_next):
        # リクエストIDを生成・設定
        request_id = set_request_id()
        start_time = time.time()
        
        # リクエストログ
        structured_logger.info(
            f"Request started: {request.method} {request.url.path}",
            event_type="request_start",
            http_method=request.method,
            path=request.url.path
        )
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # レスポンスログ
            structured_logger.api_request(
                request.method,
                request.url.path,
                response.status_code,
                duration
            )
            
            # レスポンスヘッダーにリクエストIDを追加
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            structured_logger.error(
                f"Request failed: {request.method} {request.url.path}",
                error=str(e),
                exc_info=True
            )
            raise
        finally:
            clear_request_id()

# アプリケーションに追加
app.add_middleware(LoggingMiddleware)
```

#### 統合内容：
- すべてのAPIリクエストの自動ログ
- リクエストIDの自動生成と追跡
- レスポンスヘッダーへのリクエストIDの追加
- リクエスト/レスポンス時間の計測
- エラー時の詳細ログ

## 📊 ログ出力例

### JSON形式のログ

```json
{
  "timestamp": "2025-11-22T10:30:45.123456Z",
  "level": "INFO",
  "logger": "src.workflows.atomic.chat",
  "message": "Workflow started: ChatWorkflow",
  "request_id": "abc123-def456-ghi789",
  "workflow_id": "wf-xyz789",
  "event_type": "workflow_start",
  "workflow_name": "ChatWorkflow",
  "input_keys": ["message_length", "temperature"],
  "environment": "development",
  "app_name": "LangGraph Training"
}

{
  "timestamp": "2025-11-22T10:30:45.523456Z",
  "level": "INFO",
  "logger": "src.nodes.primitives.llm.gemini.node",
  "message": "Node executed: llm_node",
  "request_id": "abc123-def456-ghi789",
  "workflow_id": "wf-xyz789",
  "node_id": "llm_node",
  "event_type": "node_execute",
  "node_name": "llm_node",
  "node_type": "LLMNode",
  "duration_seconds": 0.523,
  "duration_ms": 523.0,
  "success": true,
  "environment": "development",
  "app_name": "LangGraph Training"
}

{
  "timestamp": "2025-11-22T10:30:45.823456Z",
  "level": "INFO",
  "logger": "src.core.logging_config",
  "message": "API request: POST /workflows/chat",
  "request_id": "abc123-def456-ghi789",
  "event_type": "api_request",
  "http_method": "POST",
  "path": "/workflows/chat",
  "status_code": 200,
  "duration_seconds": 1.234,
  "duration_ms": 1234.0,
  "environment": "development",
  "app_name": "LangGraph Training"
}
```

### エラーログの例

```json
{
  "timestamp": "2025-11-22T10:30:46.123456Z",
  "level": "ERROR",
  "logger": "src.workflows.atomic.chat",
  "message": "Workflow failed: ChatWorkflow",
  "request_id": "abc123-def456-ghi789",
  "workflow_id": "wf-xyz789",
  "event_type": "workflow_end",
  "workflow_name": "ChatWorkflow",
  "duration_seconds": 0.5,
  "duration_ms": 500.0,
  "success": false,
  "error": "Message cannot be empty",
  "environment": "development",
  "app_name": "LangGraph Training"
}
```

## 🔧 設定方法

### 環境変数

`.env` ファイルでロギング設定を管理：

```env
# ロギング設定
LOG_LEVEL=INFO           # DEBUG, INFO, WARNING, ERROR, CRITICAL
APP_NAME=LangGraph Training
ENVIRONMENT=development  # development, staging, production
```

### プログラムでの設定

```python
from src.core.logging_config import setup_logging

# 基本設定
setup_logging()

# カスタム設定
setup_logging(
    log_level="DEBUG",
    log_file="logs/app.log",
    json_format=True
)
```

## 📈 使用例

### 1. ワークフローでの使用

```python
from src.core.logging_config import get_structured_logger, set_workflow_id
import time

logger = get_structured_logger(__name__)

async def run_my_workflow(input_data):
    workflow_id = set_workflow_id()
    start_time = time.time()
    
    try:
        logger.workflow_start("MyWorkflow", input_data.dict())
        
        # ワークフローロジック...
        result = await execute_workflow()
        
        duration = time.time() - start_time
        logger.workflow_end("MyWorkflow", duration, success=True)
        
        return result
        
    except Exception as e:
        duration = time.time() - start_time
        logger.workflow_end("MyWorkflow", duration, success=False, error=str(e))
        raise
```

### 2. ノードでの使用

```python
from src.core.logging_config import get_structured_logger, set_node_id
import time

logger = get_structured_logger(__name__)

async def execute(self, state):
    set_node_id(self.name)
    start_time = time.time()
    
    try:
        # ノードロジック...
        result = await process()
        
        duration = time.time() - start_time
        logger.node_execute(self.name, self.__class__.__name__, duration, True)
        
        return result
        
    except Exception as e:
        duration = time.time() - start_time
        logger.node_execute(self.name, self.__class__.__name__, duration, False)
        raise
    finally:
        clear_node_id()
```

### 3. プロバイダーでの使用

```python
from src.core.logging_config import get_structured_logger
import time

logger = get_structured_logger(__name__)

async def generate(self, prompt: str):
    start_time = time.time()
    
    try:
        response = await self._api_call(prompt)
        
        duration = time.time() - start_time
        logger.provider_call(
            self.__class__.__name__,
            "generate",
            duration,
            success=True
        )
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        logger.provider_call(
            self.__class__.__name__,
            "generate",
            duration,
            success=False
        )
        raise
```

## 🎯 ベストプラクティス

### 1. コンテキスト変数の適切な管理

```python
# ✅ 良い例: finallyでクリア
try:
    set_workflow_id()
    # 処理...
finally:
    clear_workflow_id()

# ❌ 悪い例: クリアし忘れ
set_workflow_id()
# 処理...
```

### 2. 実行時間の計測

```python
# ✅ 良い例: 開始/終了で計測
start_time = time.time()
try:
    result = await execute()
    duration = time.time() - start_time
    logger.workflow_end("MyWorkflow", duration, success=True)
finally:
    # クリーンアップ
    pass

# ❌ 悪い例: 計測なし
result = await execute()
logger.workflow_end("MyWorkflow", 0, success=True)  # 0は意味がない
```

### 3. エラー情報の記録

```python
# ✅ 良い例: 詳細なエラー情報
except Exception as e:
    logger.error(
        "Operation failed",
        error=str(e),
        error_type=type(e).__name__,
        exc_info=True  # スタックトレースを含める
    )

# ❌ 悪い例: エラー情報が不足
except Exception as e:
    logger.error("Error occurred")
```

### 4. ログレベルの適切な使用

```python
# ✅ 良い例: レベルを使い分け
logger.debug("Detailed debug information")  # 開発時のみ
logger.info("Normal operation")              # 通常の操作
logger.warning("Unusual but handled")        # 警告
logger.error("Operation failed", exc_info=True)  # エラー

# ❌ 悪い例: すべてINFO
logger.info("Debug info")
logger.info("Error occurred")
```

## 🔍 ログの分析

### 1. リクエストIDで追跡

すべてのログに含まれる`request_id`で、1つのリクエストに関連するすべてのログを追跡できます：

```bash
# リクエストIDでフィルタ
jq 'select(.request_id == "abc123-def456-ghi789")' logs/app.log
```

### 2. ワークフローIDで追跡

`workflow_id`で特定のワークフロー実行を追跡：

```bash
# ワークフローIDでフィルタ
jq 'select(.workflow_id == "wf-xyz789")' logs/app.log
```

### 3. パフォーマンス分析

実行時間でソート：

```bash
# 実行時間が長いワークフローを検索
jq 'select(.event_type == "workflow_end") | select(.duration_seconds > 1)' logs/app.log
```

### 4. エラー率の計算

```bash
# エラー率を計算
jq 'select(.event_type == "workflow_end") | .success' logs/app.log | \
  jq -s 'group_by(.) | map({key: .[0], count: length})'
```

## 📦 依存関係

構造化ロギングに必要なパッケージ：

```txt
# requirements.txtに追加済み
python-json-logger>=2.0.7
```

## ✅ テスト

### 手動テスト

```python
# src/core/logging_config.py の最後に含まれています
if __name__ == "__main__":
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("This is an info message")
    logger.warning("This is a warning", extra={"key": "value"})
    
    with LogContext(user_id="test-user"):
        logger.info("Message with context")
    
    structured_logger = get_structured_logger(__name__)
    structured_logger.workflow_start("test_workflow", {"message": "test"})
    structured_logger.node_execute("test_node", "TestNode", 0.5)
    structured_logger.workflow_end("test_workflow", 1.0, success=True)
```

実行：

```bash
cd /Users/kakegawakouichi/workspace/langgraph-training
python -m src.core.logging_config
```

### 統合テスト

既存の統合テストを実行してログ出力を確認：

```bash
pytest tests/integration/ -v
```

## 🎉 まとめ

構造化ロギングシステムの実装により、以下が実現されました：

### 実装された機能：
✅ JSON形式の構造化ログ出力  
✅ コンテキスト変数による追跡（request_id, workflow_id, node_id）  
✅ ワークフロー開始/完了の自動ログ  
✅ ノード実行の自動ログ  
✅ プロバイダー呼び出しの自動ログ  
✅ API リクエストの自動ログ  
✅ 実行時間の自動計測  
✅ エラー時の詳細ログ  
✅ リクエストIDのレスポンスヘッダーへの追加  

### メリット：
📊 **可視性**: すべての操作がJSON形式で記録され、分析が容易  
🔍 **追跡性**: リクエストID/ワークフローIDで完全な追跡が可能  
⚡ **パフォーマンス**: 実行時間が自動計測され、ボトルネック特定が容易  
🐛 **デバッグ**: 詳細なエラー情報とスタックトレースで問題解決が迅速  
📈 **分析**: JSON形式なのでログ分析ツールとの統合が容易  

### 次のステップ：
- ログ集約サービス（CloudWatch、Datadog等）との統合
- ダッシュボードの作成
- アラート設定
- ログローテーション設定

---

**実装日**: 2025-11-22  
**実装者**: AI Assistant  
**レビュー状態**: ✅ 完了

