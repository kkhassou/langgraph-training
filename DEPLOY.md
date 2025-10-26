# Renderへのデプロイ手順

このドキュメントでは、LangGraph Training APIをRenderにデプロイし、Slackと連携する手順を説明します。

## 前提条件

- Renderアカウント（https://render.com）
- Slackワークスペースとアプリ作成権限
- 各種APIキー（Gemini, GitHub, Notionなど）

## 1. Renderプロジェクトの作成

### 1.1 GitHubリポジトリの準備

```bash
# リポジトリをGitHubにプッシュ
git init
git add .
git commit -m "Initial commit for Render deployment"
git remote add origin <your-github-repo-url>
git push -u origin main
```

### 1.2 Render Dashboardでプロジェクト作成

1. https://dashboard.render.com にアクセス
2. "New +" → "Blueprint" を選択
3. GitHubリポジトリを接続
4. `render.yaml` が自動検出される

## 2. 環境変数の設定

Render Dashboardの "Environment" タブで以下の環境変数を設定：

### 必須環境変数

```bash
# Gemini API
GEMINI_API_KEY=your_gemini_api_key

# Slack (Bot User OAuth Token)
SLACK_TOKEN=xoxb-your-slack-bot-token
SLACK_SIGNING_SECRET=your_slack_signing_secret

# その他のサービス（オプション）
GITHUB_TOKEN=your_github_token
NOTION_TOKEN=your_notion_token
JIRA_TOKEN=your_jira_token
JIRA_SERVER=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com

# Google Cloud（オプション）
GOOGLE_CLOUD_PROJECT=your_project_id
```

### シークレットファイル（Google認証）

Google Services（Gmail, Calendar, Sheets等）を使用する場合：

1. Renderの "Environment" → "Secret Files" で設定
2. `/app/secrets/google_credentials.json` にサービスアカウントキーを配置
3. `/app/secrets/google_token.json` にOAuth2トークンを配置

## 3. Slackアプリの設定

### 3.1 Slackアプリの作成

1. https://api.slack.com/apps にアクセス
2. "Create New App" → "From scratch"
3. アプリ名とワークスペースを選択

### 3.2 OAuth & Permissions

**Scopes（Bot Token Scopes）を追加:**

- `app_mentions:read` - @メンションを受け取る
- `channels:history` - チャンネルメッセージを読む
- `channels:read` - チャンネル情報を取得
- `chat:write` - メッセージを送信
- `im:history` - DMを読む
- `im:read` - DM情報を取得
- `im:write` - DMを送信
- `users:read` - ユーザー情報を取得

**OAuth Token:**
- "Install to Workspace" をクリック
- 表示される `xoxb-` で始まるトークンをコピー
- RenderのEnvironmentで `SLACK_TOKEN` に設定

### 3.3 Event Subscriptions

1. "Event Subscriptions" を有効化
2. "Request URL" に以下を設定:
   ```
   https://your-app-name.onrender.com/slack/events
   ```
3. **Subscribe to bot events:**
   - `app_mention` - @メンション
   - `message.im` - ダイレクトメッセージ
   - `message.channels` - チャンネルメッセージ（必要に応じて）

### 3.4 Interactivity & Shortcuts

1. "Interactivity & Shortcuts" を有効化
2. "Request URL" に設定:
   ```
   https://your-app-name.onrender.com/slack/interactions
   ```

### 3.5 Slash Commands（オプション）

スラッシュコマンドを追加する場合：

1. "Slash Commands" → "Create New Command"
2. Command: `/todo`
3. Request URL: `https://your-app-name.onrender.com/slack/commands`
4. Description: "Create TODO items"

### 3.6 App Credentials

"Basic Information" → "App Credentials" で以下を取得:

- **Signing Secret**: RenderのEnvironmentで `SLACK_SIGNING_SECRET` に設定

## 4. デプロイ実行

### 4.1 自動デプロイ

`render.yaml` で `autoDeploy: true` が設定されているため、mainブランチへのpushで自動デプロイ:

```bash
git add .
git commit -m "Add Slack webhook integration"
git push origin main
```

### 4.2 デプロイ確認

Render Dashboardで:
1. "Logs" タブでビルド進行状況を確認
2. "Events" タブでデプロイ履歴を確認
3. デプロイ完了後、URLにアクセスしてヘルスチェック:
   ```
   https://your-app-name.onrender.com/health
   https://your-app-name.onrender.com/slack/health
   ```

## 5. Slack連携のテスト

### 5.1 URL Verification

Slackの "Event Subscriptions" でRequest URLを保存すると、Slackが自動的にチャレンジリクエストを送信します。
- 成功: ✅ Verified
- 失敗: エラーメッセージを確認してRenderのログをチェック

### 5.2 動作確認

1. **アプリをチャンネルに追加:**
   ```
   /invite @your-app-name
   ```

2. **@メンションでテスト:**
   ```
   @your-app-name こんにちは
   ```

3. **TODOワークフローのテスト:**
   ```
   @your-app-name 明日のTODO: 1. 資料作成 2. 会議準備 3. レポート提出
   ```

4. **ログ確認:**
   Render Dashboard → "Logs" で処理状況を確認

## 6. トラブルシューティング

### デプロイエラー

**ビルド失敗:**
```bash
# ローカルでDockerビルドをテスト
docker build -t langgraph-training .
docker run -p 8000:8000 langgraph-training
```

**環境変数エラー:**
- Render Dashboard → "Environment" で全ての必須変数が設定されているか確認

### Slack連携エラー

**URL Verification失敗:**
- Renderのログで `/slack/events` エンドポイントの動作確認
- `SLACK_SIGNING_SECRET` が正しく設定されているか確認

**イベント受信できない:**
- Slackアプリの "Event Subscriptions" が有効か確認
- Bot Token Scopesが正しく設定されているか確認
- アプリがチャンネルに追加されているか確認

**署名検証エラー:**
```
Invalid signature
```
- `SLACK_SIGNING_SECRET` の値を再確認
- タイムスタンプが5分以内かチェック（サーバー時刻のずれ）

### ログの確認

```bash
# Render Dashboard → Logs
# または CLI ツール
render logs --service your-service-name
```

## 7. ワークフローの拡張

### カスタムSlackハンドラーの追加

`src/api/routes_slack_webhook.py` の以下の関数を編集:

```python
async def handle_app_mention(event: Dict[str, Any]):
    """カスタムロジックを追加"""
    text = event.get("text", "")

    # 例: 特定のキーワードで異なる処理
    if "レポート" in text:
        # レポート生成ワークフローを実行
        pass
    elif "分析" in text:
        # 分析ワークフローを実行
        pass
```

### 新しいワークフローの追加

1. `src/workflows/` に新しいワークフローを作成
2. `routes_slack_webhook.py` で呼び出し
3. デプロイして動作確認

## 8. セキュリティ考慮事項

- ✅ 署名検証を必ず有効にする（`SLACK_SIGNING_SECRET`）
- ✅ 本番環境では `DEBUG=false` に設定
- ✅ 環境変数でシークレットを管理（コードに直接書かない）
- ✅ Renderの "Secret Files" で認証情報を管理
- ✅ HTTPS通信のみ（Renderが自動提供）

## 9. モニタリング

### Renderの標準機能

- **Metrics**: CPU、メモリ、ネットワーク使用量
- **Logs**: アプリケーションログ
- **Alerts**: メール通知設定

### カスタムログ

アプリケーション内で重要なイベントをログ出力:

```python
logger.info(f"TODO workflow completed: {result}")
logger.error(f"Error processing Slack event: {e}")
```

## 10. コスト最適化

### Freeプランの制限

- 750時間/月の無料枠
- 15分間アクセスがないとスリープ
- 起動に10-30秒かかる

### スリープ対策（オプション）

定期的にヘルスチェックエンドポイントを叩く:

```bash
# 外部サービス（UptimeRobot等）で設定
curl https://your-app-name.onrender.com/health
```

または、Paid プランにアップグレード（$7/月〜）

## まとめ

これでSlackからトリガーされるLangGraph Trainingワークフローが稼働します。

**次のステップ:**
- カスタムワークフローの追加
- Slack Block Kitでリッチなメッセージ作成
- 他のサービス（Notion、GitHub等）との連携強化
