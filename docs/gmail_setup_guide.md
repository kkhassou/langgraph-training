# Google Services 統合セットアップガイド

このガイドでは、Google Services（Gmail + Calendar）MCP サーバーをセットアップして、統一された認証で両方のサービスを使用する方法を説明します。

## 目次

1. [Google APIs の有効化](#1-google-apis-の有効化)
2. [OAuth 2.0 認証情報の作成](#2-oauth-20-認証情報の作成)
3. [統一トークンの生成](#3-統一トークンの生成)
4. [Google Cloud Pub/Sub のセットアップ](#4-google-cloud-pubsub-のセットアップ)
5. [Gmail Push 通知の設定](#5-gmail-push通知の設定)
6. [FastAPI エンドポイントの設定](#6-fastapiエンドポイントの設定)
7. [ワークフローの実装例](#7-ワークフローの実装例)

---

## 1. Google APIs の有効化

### 手順

1. **Google Cloud Console にアクセス**

   - [Google Cloud Console](https://console.cloud.google.com/) を開く
   - 新しいプロジェクトを作成、または既存のプロジェクトを選択

2. **必要な API を有効化**
   - 左メニューから「API とサービス」→「ライブラリ」を選択
   - 以下の API を検索して有効化:
     - **Gmail API**: 検索バーで「Gmail API」を検索 → 「有効にする」
     - **Google Calendar API**: 検索バーで「Google Calendar API」を検索 → 「有効にする」

---

## 2. OAuth 2.0 認証情報の作成

### 手順

1. **OAuth 同意画面の設定**

   - 「API とサービス」→「OAuth 同意画面」を選択
   - User Type: 「外部」を選択（個人用の場合）
   - アプリ名、サポートメール、開発者連絡先を入力
   - スコープの追加:
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/gmail.send`
     - `https://www.googleapis.com/auth/calendar.readonly`
     - `https://www.googleapis.com/auth/calendar.events`
   - **重要**: 「テストユーザー」セクションで、自分の Gmail アドレスを追加
     - 「+ ADD USERS」をクリック
     - 使用する Gmail アドレス（例: `yourname@gmail.com`）を入力
     - 「保存して次へ」をクリック

2. **認証情報の作成**

   - 「API とサービス」→「認証情報」を選択
   - 「認証情報を作成」→「OAuth クライアント ID」を選択
   - アプリケーションの種類: 「デスクトップアプリ」
   - 名前を入力して「作成」をクリック

3. **認証情報ファイルのダウンロード**
   - 作成した OAuth クライアントの右側の「⋮」→「JSON をダウンロード」
   - ダウンロードしたファイルを `credentials.json` にリネーム
   - プロジェクトルートに配置

### 環境変数の設定

`.env` ファイルに以下を追加:

```bash
# Gmail OAuth設定
GMAIL_CREDENTIALS_PATH=credentials.json
GMAIL_TOKEN_PATH=token.json
```

---

## 3. 統一トークンの生成

### 手順

1. **認証情報ファイルの配置**

   - ダウンロードした `credentials.json` を `secrets/google_credentials.json` に配置
   - 既存の `gmail_credentials.json` がある場合は、それを `google_credentials.json` にリネーム

2. **統一トークンの生成**

   ```bash
   cd /Users/kakegawakouichi/workspace/langgraph-training
   python scripts/init_google_token.py
   ```

   このスクリプトが実行されると:

   - ブラウザが自動的に開きます
   - Google アカウントでログイン
   - Gmail API と Calendar API へのアクセス許可を一度に承認
   - `secrets/google_token.json` が自動生成されます（両方のサービスで使用可能）

3. **環境変数の設定**

   `.env` ファイルに以下を設定:

   ```bash
   # Google Services API (統一設定)
   GOOGLE_CREDENTIALS_PATH=secrets/google_credentials.json
   GOOGLE_TOKEN_PATH=secrets/google_token.json

   # 後方互換性のための個別設定
   GMAIL_CREDENTIALS_PATH=secrets/google_credentials.json
   GMAIL_TOKEN_PATH=secrets/google_token.json
   CALENDAR_CREDENTIALS_PATH=secrets/google_credentials.json
   CALENDAR_TOKEN_PATH=secrets/google_token.json
   ```

---

## 4. Google Cloud Pub/Sub のセットアップ

Gmail Push 通知を受け取るには、Google Cloud Pub/Sub を使用します。

### 手順

1. **Pub/Sub API の有効化**

   - Google Cloud Console で「Pub/Sub API」を検索
   - 「有効にする」をクリック

2. **トピックの作成**

   ```bash
   # gcloud CLI を使用
   gcloud pubsub topics create gmail-notifications
   ```

3. **サブスクリプションの作成**

   ```bash
   # Push サブスクリプション（HTTPエンドポイント用）
   gcloud pubsub subscriptions create gmail-push-subscription \
     --topic=gmail-notifications \
     --push-endpoint=https://your-domain.com/api/gmail/webhook
   ```

4. **Gmail に権限を付与**
   - Gmail サービスアカウントに Pub/Sub への publish 権限を付与:
   ```bash
   gcloud pubsub topics add-iam-policy-binding gmail-notifications \
     --member=serviceAccount:gmail-api-push@system.gserviceaccount.com \
     --role=roles/pubsub.publisher
   ```

### トピック名の形式

```
projects/[YOUR-PROJECT-ID]/topics/gmail-notifications
```

例: `projects/my-project-123/topics/gmail-notifications`

---

## 4. Gmail Push 通知の設定

### API 経由での設定

```bash
# FastAPIエンドポイント経由で設定
curl -X POST "http://localhost:8000/nodes/gmail-mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "watch_inbox",
    "topic_name": "projects/[YOUR-PROJECT-ID]/topics/gmail-notifications"
  }'
```

### レスポンス例

```json
{
  "success": true,
  "data": {
    "content": [
      {
        "type": "text",
        "text": "✅ Gmail inbox watching started\nHistory ID: 12345\nExpiration: 1234567890000"
      }
    ]
  },
  "metadata": {
    "action": "watch_inbox",
    "topic": "projects/my-project/topics/gmail-notifications"
  }
}
```

### 注意点

- Watch の有効期限は 7 日間
- 定期的に再設定が必要（cron job などで自動化を推奨）

---

## 5. FastAPI エンドポイントの設定

### Webhook エンドポイントの追加

プロジェクトに以下のエンドポイントを追加します（例: `src/api/routes_gmail.py`）:

```python
from fastapi import APIRouter, Request, HTTPException
from src.services.mcp.gmail import GmailMCPService
import logging

router = APIRouter(prefix="/api/gmail", tags=["gmail"])
logger = logging.getLogger(__name__)

gmail_service = GmailMCPService()

@router.post("/webhook")
async def gmail_webhook(request: Request):
    """Gmail Pub/Sub からの通知を受信"""
    try:
        # Pub/Sub メッセージの取得
        body = await request.json()
        message = body.get("message", {})

        # メッセージデータのデコード
        import base64
        import json

        if "data" in message:
            decoded_data = base64.b64decode(message["data"]).decode("utf-8")
            notification = json.loads(decoded_data)

            email_address = notification.get("emailAddress")
            history_id = notification.get("historyId")

            logger.info(f"Received Gmail notification for {email_address}, historyId: {history_id}")

            # 新しいメッセージを取得
            result = await gmail_service.get_messages(query="is:unread", max_results=1)

            # ここでワークフローをトリガー
            # 例: LangGraphワークフローの起動
            # await trigger_workflow(result)

            return {"status": "success", "message": "Notification processed"}

        return {"status": "no_data"}

    except Exception as e:
        logger.error(f"Error processing Gmail webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### main.py への追加

```python
from src.api import routes_gmail

# ルーターの追加
app.include_router(routes_gmail.router)
```

---

## 6. ワークフローの実装例

### 自分宛のメールでワークフローを起動

```python
from langchain_core.messages import HumanMessage
from src.graphs.simple_chat import simple_chat_graph
from src.services.mcp.gmail import GmailMCPService

async def trigger_email_workflow(email_data: dict):
    """メール受信をトリガーにワークフローを実行"""
    gmail_service = GmailMCPService()

    # メール内容を取得
    messages = email_data.get("messages", [])
    if not messages:
        return

    latest_email = messages[0]
    subject = latest_email.get("subject", "")
    body = latest_email.get("body", "")
    sender = latest_email.get("from", "")

    # ワークフローの入力を作成
    workflow_input = {
        "messages": [
            HumanMessage(content=f"Subject: {subject}\n\nFrom: {sender}\n\n{body}")
        ]
    }

    # LangGraphワークフローを実行
    result = await simple_chat_graph.ainvoke(workflow_input)

    # 結果をメールで返信
    response_text = result["messages"][-1].content

    await gmail_service.send_message(
        to=sender,
        subject=f"Re: {subject}",
        body=f"自動応答:\n\n{response_text}"
    )

    return result
```

### webhook エンドポイントの完全版

```python
@router.post("/webhook")
async def gmail_webhook(request: Request):
    """Gmail Pub/Sub からの通知を受信してワークフローを起動"""
    try:
        body = await request.json()
        message = body.get("message", {})

        if "data" in message:
            import base64
            import json

            decoded_data = base64.b64decode(message["data"]).decode("utf-8")
            notification = json.loads(decoded_data)

            # 新しいメッセージを取得
            result = await gmail_service.get_messages(query="is:unread", max_results=1)

            # ワークフローを起動
            workflow_result = await trigger_email_workflow(result)

            return {
                "status": "success",
                "workflow_executed": True,
                "result": workflow_result
            }

        return {"status": "no_data"}

    except Exception as e:
        logger.error(f"Error processing Gmail webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 使用例

### 1. 認証

初回実行時、ブラウザが開いて Google アカウントでの認証を求められます:

```bash
python -m src.mcp_servers.gmail.server
```

認証後、`token.json` が作成され、以降は自動的に認証されます。

### 2. メッセージの取得

```bash
curl -X POST "http://localhost:8000/nodes/gmail-mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "get_messages",
    "query": "is:unread",
    "max_results": 5
  }'
```

### 3. メールの送信

```bash
curl -X POST "http://localhost:8000/nodes/gmail-mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "send_message",
    "to": "recipient@example.com",
    "subject": "Test Email",
    "body": "This is a test email sent via Gmail MCP"
  }'
```

### 4. Watch 設定

```bash
curl -X POST "http://localhost:8000/nodes/gmail-mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "watch_inbox",
    "topic_name": "projects/my-project/topics/gmail-notifications"
  }'
```

---

## トラブルシューティング

### 1. 認証エラー

**問題**: `credentials.json` が見つからない

**解決策**:

- `credentials.json` がプロジェクトルートにあることを確認
- `.env` の `GMAIL_CREDENTIALS_PATH` が正しいことを確認

### 2. Pub/Sub エラー

**問題**: Push 通知が届かない

**解決策**:

- トピック名が正しいか確認
- Gmail サービスアカウントに publish 権限があるか確認
- Webhook エンドポイントが公開されているか確認（ngrok などを使用）

### 3. Watch の期限切れ

**問題**: 7 日後に通知が止まる

**解決策**:

- Cron job で定期的に watch を再設定

```python
import schedule
import time

async def refresh_watch():
    service = GmailMCPService()
    await service.watch_inbox("projects/my-project/topics/gmail-notifications")

# 毎日実行
schedule.every().day.at("00:00").do(refresh_watch)
```

---

## セキュリティ上の注意

1. **認証情報の管理**

   - `credentials.json` と `token.json` を `.gitignore` に追加
   - 本番環境では環境変数や秘密管理サービスを使用

2. **Webhook 検証**

   - Pub/Sub メッセージの署名を検証
   - IP ホワイトリストの設定を推奨

3. **スコープの最小化**
   - 必要最小限の Gmail API スコープのみを要求
   - 定期的なアクセストークンのローテーション

---

## 次のステップ

1. ワークフローの拡張（RAG、Slack 通知など）
2. エラーハンドリングの強化
3. ログとモニタリングの実装
4. 本番環境へのデプロイ

詳細は [Gmail API 公式ドキュメント](https://developers.google.com/gmail/api) を参照してください。
