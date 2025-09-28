# 📁 LangGraph Training プロジェクト ファイル構成解説

## 🏗️ プロジェクト全体構造

```
langgraph-training/
├── 📦 基本設定・環境
├── 🔧 アプリケーション本体 (app/)
├── 🌐 MCPサーバー (mcp_servers/)
├── ⚙️ 設定ファイル (config/)
├── 📚 ドキュメント (docs/)
├── 🛠️ スクリプト (scripts/)
└── 🧪 テストファイル
```

## 📦 基本設定・環境ファイル

### `Dockerfile`

- **役割**: Docker コンテナ設定
- **内容**: Python 3.11 ベース、必要なパッケージのインストール
- **用途**: 本番環境でのコンテナ化

### `docker-compose.yml`

- **役割**: Docker Compose 設定
- **内容**: 開発環境用のコンテナオーケストレーション
- **用途**: `docker-compose up`で簡単起動

### `requirements.txt`

- **役割**: Python パッケージ依存関係
- **内容**: FastAPI、LangGraph、各種 API クライアント
- **用途**: `pip install -r requirements.txt`

### `README.md`

- **役割**: プロジェクト全体のドキュメント
- **内容**: セットアップ手順、使用方法、MCP 対応説明
- **用途**: 開発者向けガイド

## 🔧 アプリケーション本体 (`app/`)

### 🏠 エントリーポイント

#### `app/main.py`

- **役割**: メイン FastAPI アプリケーション
- **内容**: 完全版（Slack/Jira 統合込み）
- **特徴**: Swagger UI、CORS 設定、ルーター統合

### 🌐 API レイヤー (`app/api/`)

#### `app/api/routes_nodes.py`

- **役割**: 個別ノード用 API エンドポイント
- **エンドポイント**:
  - `POST /nodes/gemini` - LLM 文章生成
  - `POST /nodes/ppt-ingest` - PowerPoint 解析
  - `POST /nodes/slack` - Slack 直接統合
  - `POST /nodes/jira` - Jira 直接統合
  - `POST /nodes/slack-mcp` - Slack MCP 統合
  - `POST /nodes/jira-mcp` - Jira MCP 統合

#### `app/api/routes_nodes_minimal.py`

- **役割**: 最小版ノード API エンドポイント
- **内容**: Gemini + PPT Ingest のみ

#### `app/api/routes_graphs.py`

- **役割**: ワークフローグラフ用 API エンドポイント
- **エンドポイント**:
  - `POST /graphs/simple-chat` - 基本チャット
  - `POST /graphs/ppt-summary` - PPT 要約ワークフロー
  - `POST /graphs/slack-report` - Slack レポート生成
  - `POST /graphs/reflection` - 反復改善パターン
  - `POST /graphs/chain-of-thought` - 段階的思考パターン

### 🧠 ノード層 (`app/nodes/`)

#### `app/nodes/base_node.py` 🏗️

- **役割**: 全ノードの基底クラス
- **内容**:
  - `NodeState`: ノード間データ共有
  - `BaseNode`: 抽象基底クラス
  - `NodeInput/Output`: 入出力モデル

#### 基本ノード

##### `app/nodes/llm_gemini.py`

- **役割**: Google Gemini LLM 統合
- **機能**: テキスト生成、対話応答
- **API**: Google Generative AI

##### `app/nodes/ppt_ingest.py`

- **役割**: PowerPoint ファイル解析
- **機能**: スライドからテキスト抽出
- **ライブラリ**: python-pptx

#### 直接統合ノード (`app/nodes/direct_integrations/`)

##### `app/nodes/direct_integrations/slack_node.py`

- **役割**: Slack 直接 API 統合
- **機能**: メッセージ取得/送信、チャンネル管理
- **依存**: slack-sdk

##### `app/nodes/direct_integrations/jira_node.py`

- **役割**: Jira 直接 API 統合
- **機能**: チケット作成/更新、プロジェクト管理
- **依存**: jira

#### MCP 統合ノード (`app/nodes/mcp_integrations/`)

##### `app/nodes/mcp_integrations/mcp_base.py`

- **役割**: MCP 統合ノードの基底クラス
- **機能**: MCP クライアント管理、エラーハンドリング

##### `app/nodes/mcp_integrations/slack_mcp_node.py`

- **役割**: Slack MCP 統合
- **特徴**: MCP サーバー経由で Slack 操作

##### `app/nodes/mcp_integrations/jira_mcp_node.py`

- **役割**: Jira MCP 統合
- **特徴**: MCP サーバー経由で Jira 操作

### 🔄 ワークフロー層 (`app/graphs/`)

#### `app/graphs/simple_chat.py`

- **役割**: 基本的なチャットワークフロー
- **構成**: ユーザー入力 → Gemini LLM → 応答

#### `app/graphs/ppt_summary.py`

- **役割**: PowerPoint 要約ワークフロー
- **構成**: PPT ファイル → テキスト抽出 → LLM 要約 → 結果

#### `app/graphs/slack_report.py`

- **役割**: Slack レポート生成ワークフロー
- **構成**: Slack メッセージ収集 → 分析 → レポート生成

### 🧩 デザインパターン (`app/patterns/`)

#### `app/patterns/reflection.py`

- **役割**: リフレクション（反復改善）パターン
- **機能**:
  - 初期回答生成
  - 自己評価・フィードバック
  - 改善された回答生成
- **用途**: 品質向上、複数回の推敲

#### `app/patterns/chain_of_thought.py`

- **役割**: Chain of Thought（段階的思考）パターン
- **機能**:
  - 問題の分解
  - ステップ別推論
  - 最終結論の統合
- **用途**: 複雑な問題解決

### 🔌 サービス層 (`app/services/`)

#### 直接統合サービス (`app/services/direct_services/`)

##### `app/services/direct_services/slack_service.py`

- **役割**: Slack API 直接操作
- **機能**: メッセージ、チャンネル、ユーザー管理

##### `app/services/direct_services/jira_service.py`

- **役割**: Jira API 直接操作
- **機能**: プロジェクト、イシュー、ワークフロー管理

#### MCP 統合サービス (`app/services/mcp_services/`)

##### `app/services/mcp_services/slack_mcp_service.py`

- **役割**: Slack MCP 操作
- **特徴**: MCP 経由で Slack 機能を抽象化

##### `app/services/mcp_services/jira_mcp_service.py`

- **役割**: Jira MCP 操作
- **特徴**: MCP 経由で Jira 機能を抽象化

### ⚙️ 設定・共通機能 (`app/core/`)

#### `app/core/config.py`

- **役割**: アプリケーション設定管理
- **内容**: API キー、環境変数の管理
- **特徴**: .env ファイル対応

#### `app/core/dependencies.py`

- **役割**: 依存性注入・バリデーション
- **機能**: API キー検証、設定値の提供

## 🌐 MCP サーバー (`mcp_servers/`)

### Slack MCP サーバー (`mcp_servers/slack/`)

#### `mcp_servers/slack/server.py` 🌐

- **役割**: Slack MCP サーバー実装
- **プロトコル**: Model Context Protocol
- **機能**: Slack API を MCP ツールとして公開

#### `mcp_servers/slack/config.json`

- **役割**: Slack MCP サーバー設定
- **内容**: 利用可能ツール一覧、環境変数定義

#### `mcp_servers/slack/requirements.txt`

- **役割**: Slack MCP サーバー専用依存関係

### Jira MCP サーバー (`mcp_servers/jira/`)

#### `mcp_servers/jira/server.py` 🌐

- **役割**: Jira MCP サーバー実装
- **プロトコル**: Model Context Protocol
- **機能**: Jira API を MCP ツールとして公開

#### `mcp_servers/jira/config.json`

- **役割**: Jira MCP サーバー設定

#### `mcp_servers/jira/requirements.txt`

- **役割**: Jira MCP サーバー専用依存関係

### 共有ユーティリティ (`mcp_servers/shared/`)

#### `mcp_servers/shared/utils.py`

- **役割**: MCP サーバー共通機能
- **内容**: ログ設定、エラーハンドリング、JSON 操作

## ⚙️ 設定ファイル (`config/`)

### `config/mcp_config.json`

- **役割**: MCP 統合の中央設定
- **内容**: サーバー定義、コマンド、環境変数

### `config/claude_desktop_config.json`

- **役割**: Claude Desktop 用 MCP 設定
- **用途**: Claude で MCP サーバーを直接使用

## 📚 ドキュメント (`docs/`)

### `docs/workshop_guide.md`

- **役割**: ワークショップ進行ガイド
- **内容**: 学習手順、演習課題、学習目標

### `docs/file_structure_guide.md` (このファイル)

- **役割**: プロジェクト構成の詳細解説
- **内容**: 各ファイルの役割と責任範囲

## 🛠️ スクリプト (`scripts/`)

### `scripts/run_local.py`

- **役割**: ローカル開発サーバー起動
- **機能**: 依存関係チェック、Uvicorn 起動

### `scripts/generate_diagram.py`

- **役割**: ワークフロー図生成
- **出力**: Mermaid 図、HTML 可視化

## 🧪 テスト・開発支援

### `test_ppt.py`

- **役割**: PPT Ingest 機能のテスト
- **用途**: 単体機能の動作確認

## 🗂️ ファイル役割まとめ

| 分類                   | 主要ファイル                   | 責任範囲                 |
| ---------------------- | ------------------------------ | ------------------------ |
| **エントリーポイント** | `main.py`                      | アプリケーション起動     |
| **API 層**             | `routes_*.py`                  | REST API エンドポイント  |
| **処理層**             | `nodes/*.py`                   | 個別機能の実装           |
| **統合層**             | `graphs/*.py`                  | 複数ノードのワークフロー |
| **パターン層**         | `patterns/*.py`                | 高度な AI 処理パターン   |
| **サービス層**         | `services/*.py`                | 外部 API 統合            |
| **MCP 層**             | `mcp_servers/*.py`             | 標準化されたツール提供   |
| **設定層**             | `config/*.py`, `config/*.json` | 環境・設定管理           |

## 🎯 開発時の参考

### 新機能追加の流れ

1. **サービス層**: 外部 API 統合 (`services/`)
2. **ノード層**: 個別機能実装 (`nodes/`)
3. **API 層**: エンドポイント追加 (`api/`)
4. **統合層**: ワークフロー作成 (`graphs/`)

### デバッグ時の確認ポイント

1. **設定**: `config.py`で環境変数確認
2. **依存関係**: `requirements.txt`で必要パッケージ確認
3. **ログ**: 各ノードのエラーメッセージ
4. **テスト**: 個別ノードの単体テスト

この構成により、**段階的学習**と**実用的な拡張**の両方が可能な、体系的な LangGraph トレーニング環境を提供しています。
