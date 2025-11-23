# 監視とロギング強化完了レポート

**実施日**: 2025年11月22日  
**目的**: 構造化ロギング（JSON形式）とPrometheusメトリクス収集の実装  
**ステータス**: ✅ 完了

---

## 📋 実施内容

### 1. 構造化ロギングの実装（JSON形式）

**新規ファイル**: `src/core/logging_config.py` (約400行)

#### 主な機能

1. **JSON形式のログ出力**
   ```json
   {
     "timestamp": "2025-11-22T10:30:45.123Z",
     "level": "INFO",
     "logger": "src.workflows.chat",
     "message": "Chat workflow started",
     "request_id": "550e8400-e29b-41d4-a716-446655440000",
     "user_id": "user123",
     "environment": "production",
     "app_name": "LangGraph Training"
   }
   ```

2. **コンテキスト情報の自動追加**
   - タイムスタンプ（ISO 8601形式）
   - ログレベル
   - ロガー名
   - ファイル情報（パス、行番号、関数名）
   - リクエストID（コンテキスト変数から自動取得）
   - ユーザーID（コンテキスト変数から自動取得）
   - 環境情報

3. **LogContext コンテキストマネージャー**
   ```python
   with LogContext(request_id="req-123", user_id="user-456"):
       logger.info("Processing request")
       # request_id と user_id が自動的にログに含まれる
   ```

4. **関数呼び出しログ用デコレーター**
   ```python
   @log_function_call(logger)
   async def process_data(data):
       return data
   
   # 関数の開始・完了・エラーが自動的にログに記録される
   ```

---

### 2. Prometheusメトリクスの実装

**新規ファイル**: `src/core/metrics.py` (約400行)

#### 収集するメトリクス

##### LLMメトリクス
- `langgraph_llm_requests_total`: LLM呼び出し回数（Counter）
  - ラベル: provider, model, method
- `langgraph_llm_request_duration_seconds`: LLMリクエスト時間（Histogram）
  - バケット: 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0秒
- `langgraph_llm_tokens_total`: トークン使用量（Counter）
  - ラベル: provider, model, type (input/output)
- `langgraph_llm_errors_total`: LLMエラー回数（Counter）
  - ラベル: provider, model, error_type

##### ワークフローメトリクス
- `langgraph_workflow_executions_total`: ワークフロー実行回数（Counter）
  - ラベル: workflow_name, status (success/failure)
- `langgraph_workflow_duration_seconds`: ワークフロー実行時間（Histogram）
  - バケット: 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0秒
- `langgraph_workflow_errors_total`: ワークフローエラー回数（Counter）
  - ラベル: workflow_name, error_type

##### ノードメトリクス
- `langgraph_node_executions_total`: ノード実行回数（Counter）
  - ラベル: node_name, node_type, status
- `langgraph_node_duration_seconds`: ノード実行時間（Histogram）
  - バケット: 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0秒
- `langgraph_node_errors_total`: ノードエラー回数（Counter）
  - ラベル: node_name, node_type, error_type

##### RAGメトリクス
- `langgraph_rag_queries_total`: RAGクエリ回数（Counter）
- `langgraph_rag_query_duration_seconds`: RAGクエリ時間（Histogram）
- `langgraph_rag_documents_retrieved`: 取得ドキュメント数（Histogram）

##### システムメトリクス
- `langgraph_active_requests`: アクティブリクエスト数（Gauge）
- `langgraph_http_requests_total`: HTTPリクエスト回数（Counter）
- `langgraph_http_request_duration_seconds`: HTTPリクエスト時間（Histogram）

##### プラグインメトリクス
- `langgraph_plugins_loaded_total`: 読み込まれたプラグイン数（Gauge）
- `langgraph_plugin_load_errors_total`: プラグイン読み込みエラー回数（Counter）

---

## 💡 使用方法

### 1. ロギングの設定

```python
from src.core.logging_config import setup_logging, get_logger

# ロギングを初期化
setup_logging(
    log_level="INFO",
    log_file="logs/app.log",  # オプション
    json_format=True  # JSON形式で出力
)

# ロガーを取得
logger = get_logger(__name__)

# ログを出力
logger.info("Application started")
logger.warning("Low memory", extra={"memory_mb": 100})
logger.error("Error occurred", extra={"error_code": "E001"})
```

### 2. コンテキスト情報の設定

```python
from src.core.logging_config import LogContext

# コンテキストマネージャーを使用
with LogContext(request_id="req-123", user_id="user-456"):
    logger.info("Processing request")
    # ログにrequest_idとuser_idが自動的に含まれる
```

### 3. メトリクスの収集

```python
from src.core.metrics import metrics

# LLM呼び出しをカウント
metrics.llm_requests_total.labels(
    provider="gemini",
    model="gemini-2.0-flash-exp",
    method="generate"
).inc()

# レスポンス時間を記録
with metrics.track_llm_request("gemini", "gemini-2.0-flash-exp", "generate"):
    response = await provider.generate("Hello")
```

### 4. メトリクスの公開

```python
from fastapi import FastAPI, Response
from src.core.metrics import get_metrics_text, CONTENT_TYPE_LATEST

app = FastAPI()

@app.get("/metrics")
async def metrics_endpoint():
    """Prometheusメトリクスエンドポイント"""
    return Response(
        content=metrics.get_metrics(),
        media_type=CONTENT_TYPE_LATEST
    )
```

### 5. デコレーターの使用

```python
from src.core.logging_config import log_function_call, get_logger
from src.core.metrics import track_metrics

logger = get_logger(__name__)

# ロギングデコレーター
@log_function_call(logger)
async def process_data(data):
    return data

# メトリクスデコレーター
@track_metrics('llm', provider='gemini', model='gemini-2.0-flash-exp', method='generate')
async def generate_text(prompt):
    return await provider.generate(prompt)
```

---

## 📊 改善効果

### Before（基本的なロギング）

```python
# 通常のテキストログ
logging.info("Processing request")
# Output: 2025-11-22 10:30:45 - INFO - Processing request
```

**問題点**:
- ❌ 構造化されていない
- ❌ コンテキスト情報が不足
- ❌ ログ解析が困難
- ❌ メトリクスなし
- ❌ トレーサビリティが低い

### After（構造化ロギング + メトリクス）

```python
# JSON形式のログ
with LogContext(request_id="req-123", user_id="user-456"):
    logger.info("Processing request", extra={"operation": "generate"})

# Output:
# {
#   "timestamp": "2025-11-22T10:30:45.123Z",
#   "level": "INFO",
#   "logger": "src.workflows.chat",
#   "message": "Processing request",
#   "request_id": "req-123",
#   "user_id": "user-456",
#   "operation": "generate",
#   "environment": "production"
# }

# メトリクス
with metrics.track_llm_request("gemini", "gemini-2.0-flash-exp", "generate"):
    response = await provider.generate("Hello")
```

**メリット**:
- ✅ 構造化されたJSON形式
- ✅ 豊富なコンテキスト情報
- ✅ ログ解析が容易
- ✅ Prometheusメトリクス収集
- ✅ 高いトレーサビリティ
- ✅ パフォーマンス監視

---

## 🔧 Prometheus統合

### 1. Prometheusの設定

**`prometheus.yml`**:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'langgraph'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### 2. Grafanaダッシュボード

#### LLMダッシュボード

```promql
# LLM呼び出し率（1分間）
rate(langgraph_llm_requests_total[1m])

# LLM平均レスポンス時間
histogram_quantile(0.5, 
  rate(langgraph_llm_request_duration_seconds_bucket[5m])
)

# LLMエラー率
rate(langgraph_llm_errors_total[5m]) / 
rate(langgraph_llm_requests_total[5m])
```

#### ワークフローダッシュボード

```promql
# ワークフロー実行回数
sum by (workflow_name) (
  langgraph_workflow_executions_total
)

# ワークフロー成功率
sum by (workflow_name) (
  langgraph_workflow_executions_total{status="success"}
) / sum by (workflow_name) (
  langgraph_workflow_executions_total
)

# ワークフロー実行時間（P95）
histogram_quantile(0.95,
  sum by (workflow_name, le) (
    rate(langgraph_workflow_duration_seconds_bucket[5m])
  )
)
```

---

## 🎯 主な機能

### 1. 構造化ロギング

- ✅ JSON形式の出力
- ✅ カスタムフィールドの追加
- ✅ コンテキスト変数（リクエストID、ユーザーID）
- ✅ ファイルとコンソールへの出力
- ✅ ログレベルの動的設定

### 2. メトリクス収集

- ✅ Counter（累積カウンター）
- ✅ Gauge（現在値）
- ✅ Histogram（分布）
- ✅ ラベルによる分類
- ✅ 自動時間計測

### 3. コンテキスト管理

- ✅ コンテキストマネージャー
- ✅ デコレーター
- ✅ 自動クリーンアップ
- ✅ ネストしたコンテキスト

### 4. 統合

- ✅ FastAPI統合
- ✅ LangGraph統合
- ✅ Prometheus統合
- ✅ Grafana統合

---

## 📈 品質指標

### ロギング

- ✅ JSON形式: 100%
- ✅ コンテキスト情報: リクエストID、ユーザーID、環境
- ✅ タイムスタンプ: ISO 8601形式
- ✅ ログレベル: DEBUG, INFO, WARNING, ERROR, CRITICAL

### メトリクス

- ✅ メトリクスタイプ: 15+種類
- ✅ LLMメトリクス: 4種類
- ✅ ワークフローメトリクス: 3種類
- ✅ ノードメトリクス: 3種類
- ✅ システムメトリクス: 3種類

---

## 🔮 今後の拡張

### 1. 分散トレーシング

```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerExporter

# OpenTelemetryとの統合
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("llm_request"):
    response = await provider.generate("Hello")
```

### 2. アラート設定

```yaml
# Prometheus Alert Rules
groups:
  - name: langgraph_alerts
    rules:
      - alert: HighErrorRate
        expr: |
          rate(langgraph_llm_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High LLM error rate detected"
```

### 3. ログ集約

```python
# ELKスタック、Splunkなどとの統合
# JSON形式のログは直接取り込み可能
```

---

## ✅ まとめ

監視とロギングの強化により、以下を達成しました：

1. **JSON形式の構造化ロギング** - ログ解析が容易に
2. **Prometheusメトリクス収集** - パフォーマンス監視が可能に
3. **コンテキスト情報の自動追加** - トレーサビリティが向上
4. **15+種類のメトリクス** - 詳細な監視が可能
5. **便利なヘルパー** - コンテキストマネージャー、デコレーター
6. **本番運用対応** - エンタープライズグレードの監視機能

このプロジェクトは、**本番環境で使用できる監視・ロギング基盤**を実現しました。

---

*完了日: 2025年11月22日*  
*ステータス: ✅ 全改善完了*

