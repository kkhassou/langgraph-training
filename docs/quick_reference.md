# 🚀 LangGraph Training クイックリファレンス

## 📋 よく使うファイル一覧

### 🏃‍♂️ 起動・実行

```bash
# アプリ起動
python app/main.py

# Docker起動
docker-compose up
```

### 🔧 主要設定ファイル

| ファイル             | 用途           | 編集頻度   |
| -------------------- | -------------- | ---------- |
| `.env`               | API キー設定   | 初回のみ   |
| `app/core/config.py` | アプリ設定     | 稀         |
| `requirements.txt`   | パッケージ管理 | 機能追加時 |

### 🌐 API エンドポイント

| URL                            | 機能       | 主要用途         |
| ------------------------------ | ---------- | ---------------- |
| `http://localhost:8000/docs`   | Swagger UI | API テスト       |
| `http://localhost:8000/`       | ホーム     | 概要確認         |
| `http://localhost:8000/nodes/` | ノード一覧 | 利用可能機能確認 |

## 🔍 ファイル検索ガイド

### 機能別ファイル位置

#### LLM・AI 機能

- **Gemini 統合**: `app/nodes/llm_gemini.py`
- **思考パターン**: `app/patterns/`
- **ワークフロー**: `app/graphs/`

#### 外部サービス統合

- **Slack 直接**: `app/services/direct_services/slack_service.py`
- **Slack MCP**: `app/services/mcp_services/slack_mcp_service.py`
- **Jira 直接**: `app/services/direct_services/jira_service.py`
- **Jira MCP**: `app/services/mcp_services/jira_mcp_service.py`

#### ファイル処理

- **PowerPoint**: `app/nodes/ppt_ingest.py`

#### API・Web

- **個別機能 API**: `app/api/routes_nodes.py`
- **ワークフロー API**: `app/api/routes_graphs.py`
- **メインアプリ**: `app/main.py`

## 🛠️ 開発フロー

### 1. 新しいノード追加

1. `app/nodes/` にノードファイル作成
2. `app/api/routes_nodes.py` にエンドポイント追加
3. テスト実行

### 2. 新しいワークフロー作成

1. `app/graphs/` にグラフファイル作成
2. `app/api/routes_graphs.py` にエンドポイント追加
3. `scripts/generate_diagram.py` で図生成

### 3. 外部サービス統合

#### 直接統合の場合

1. `app/services/direct_services/` にサービス作成
2. `app/nodes/direct_integrations/` にノード作成

#### MCP 統合の場合

1. `mcp_servers/service_name/` に MCP サーバー作成
2. `app/services/mcp_services/` にサービス作成
3. `app/nodes/mcp_integrations/` にノード作成

## 🐛 トラブルシューティング

### よくある問題と解決方法

#### インポートエラー

```python
# ModuleNotFoundError: No module named 'xxx'
pip install -r requirements.txt
```

#### API キーエラー

```bash
# .envファイルを確認
cp .env.example .env
vim .env  # API キーを設定
```

#### Slack/Jira 統合エラー

```bash
# 依存関係不足の場合
pip install slack-sdk jira

# 依存関係を確認してインストール
pip install -r requirements.txt
```

#### PPT 処理エラー

```bash
# python-pptx が必要
pip install python-pptx

# テスト実行
python test_ppt.py
```

### ログ確認方法

```bash
# アプリケーションログ
tail -f app.log

# Docker ログ
docker-compose logs -f

# MCPサーバーログ
tail -f mcp_servers/slack/server.log
```

## 📂 ディレクトリ構造（簡易版）

```
📁 app/
  ├── 🏠 main.py                     # アプリ起動
  ├── 🌐 api/                        # REST API
  ├── 🧠 nodes/                      # 個別機能
  ├── 🔄 graphs/                     # ワークフロー
  ├── 🧩 patterns/                   # AIパターン
  ├── 🔌 services/                   # 外部統合
  └── ⚙️ core/                       # 設定・共通

📁 mcp_servers/                      # MCPサーバー
📁 config/                           # 設定ファイル
📁 docs/                             # ドキュメント
📁 scripts/                          # ユーティリティ
```

## 🎯 学習の進め方

### 初心者向け

1. `docs/workshop_guide.md` を読む
2. `app/main.py` で基本機能を試す
3. `app/nodes/` の個別ノードを理解
4. `app/graphs/simple_chat.py` でワークフロー学習

### 中級者向け

1. `app/patterns/` のデザインパターン学習
2. 新しいノード作成練習
3. MCP サーバー理解と作成
4. 複雑なワークフロー構築

### 上級者向け

1. カスタムパターン設計
2. 新しい外部サービス統合
3. パフォーマンス最適化
4. 本番環境デプロイ

## 📚 参考リンク

- **詳細ガイド**: `docs/file_structure_guide.md`
- **ワークショップ**: `docs/workshop_guide.md`
- **README**: `README.md`
- **API ドキュメント**: `http://localhost:8000/docs`
