# Google Calendar セットアップガイド

Google Calendar MCP サーバーを使用するための設定手順です。

## 前提条件

- Google Cloud Console でプロジェクトが作成済み
- OAuth 2.0 認証情報（`credentials.json`）が存在する

## セットアップ手順

### 1. Google Cloud Console で Calendar API を有効化

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. プロジェクトを選択
3. 左メニューから「API とサービス」→「ライブラリ」を選択
4. 検索バーで「Google Calendar API」を検索
5. 「Google Calendar API」を選択し、「有効にする」をクリック

### 2. OAuth 同意画面の設定（既存の場合はスキップ可）

1. 「API とサービス」→「OAuth 同意画面」を選択
2. スコープに以下を追加:
   - `https://www.googleapis.com/auth/calendar.readonly`
   - `https://www.googleapis.com/auth/calendar.events`
3. 既存の Gmail スコープも維持:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.send`

### 3. 環境変数の確認

`.env`ファイルに以下が設定されているか確認:

```bash
# Google Services API (統一設定)
GOOGLE_CREDENTIALS_PATH=secrets/google_credentials.json
GOOGLE_TOKEN_PATH=secrets/google_token.json

# 後方互換性のための個別設定
CALENDAR_CREDENTIALS_PATH=secrets/google_credentials.json
CALENDAR_TOKEN_PATH=secrets/google_token.json
GMAIL_CREDENTIALS_PATH=secrets/google_credentials.json
GMAIL_TOKEN_PATH=secrets/google_token.json
```

### 4. 認証トークンの生成

#### 方法 1: スクリプトを使用（推奨）

```bash
cd /Users/kakegawakouichi/workspace/langgraph-training
python scripts/init_google_token.py
```

このスクリプトが実行されると:

1. ブラウザが自動的に開きます
2. Google アカウントでログイン
3. Calendar API へのアクセス許可を承認
4. `secrets/google_token.json`が自動生成されます（Gmail と Calendar の両方で使用可能）

#### 方法 2: 手動で認証

```bash
cd /Users/kakegawakouichi/workspace/langgraph-training
python -c "
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events'
]

flow = InstalledAppFlow.from_client_secrets_file(
    'secrets/google_credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

with open('secrets/google_token.json', 'w') as token:
    token.write(creds.to_json())

print('✅ Token saved to secrets/google_token.json')
"
```

### 5. 動作確認

FastAPI サーバーを起動して、エンドポイントをテスト:

```bash
# サーバー起動
cd /Users/kakegawakouichi/workspace/langgraph-training
python -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

#### イベント一覧の取得

```bash
curl -X POST "http://localhost:8001/nodes/calendar-mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "list_events",
    "max_results": 5
  }'
```

#### イベントの作成

```bash
curl -X POST "http://localhost:8001/nodes/calendar-mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_event",
    "summary": "テスト会議",
    "start_time": "2025-10-15T10:00:00",
    "end_time": "2025-10-15T11:00:00",
    "location": "会議室A",
    "description": "テストイベントです"
  }'
```

## トラブルシューティング

### エラー: "Calendar client is not initialized"

**原因**: 認証トークンが生成されていない

**解決策**:

1. `secrets/google_token.json`が存在するか確認
2. 存在しない場合、手順 4 を実行して認証トークンを生成

### エラー: "invalid_grant" または "Token has been expired or revoked"

**原因**: トークンが期限切れまたは無効

**解決策**:

```bash
# トークンファイルを削除して再生成
rm secrets/google_token.json
python scripts/init_google_token.py
```

### エラー: "The caller does not have permission"

**原因**: OAuth 同意画面で Calendar API スコープが追加されていない

**解決策**:

1. Google Cloud Console で「OAuth 同意画面」を開く
2. スコープセクションで Calendar API スコープを追加
3. トークンを再生成

### エラー: "API has not been used in project"

**原因**: Calendar API が有効化されていない

**解決策**:

1. [Google Cloud Console](https://console.cloud.google.com/)で Calendar API を有効化
2. 数分待ってから再試行

## Calendar API の機能

### 1. list_events - イベント一覧取得

```json
{
  "action": "list_events",
  "calendar_id": "primary",
  "max_results": 10,
  "time_min": "2025-10-01T00:00:00Z",
  "time_max": "2025-10-31T23:59:59Z"
}
```

### 2. create_event - イベント作成

```json
{
  "action": "create_event",
  "summary": "会議タイトル",
  "start_time": "2025-10-15T10:00:00",
  "end_time": "2025-10-15T11:00:00",
  "description": "会議の説明",
  "location": "会議室A",
  "attendees": ["user1@example.com", "user2@example.com"]
}
```

### 3. update_event - イベント更新

```json
{
  "action": "update_event",
  "event_id": "イベントID",
  "summary": "新しいタイトル",
  "start_time": "2025-10-15T14:00:00",
  "end_time": "2025-10-15T15:00:00"
}
```

### 4. delete_event - イベント削除

```json
{
  "action": "delete_event",
  "event_id": "イベントID"
}
```

## 統合例: Gmail と Calendar の連携

メール内容をもとにカレンダーイベントを自動作成:

```python
from src.services.mcp.gmail import GmailMCPService
from src.services.mcp.google_calendar import CalendarMCPService

async def create_event_from_email():
    # Gmailからメール取得
    gmail = GmailMCPService()
    messages = await gmail.get_messages(query="is:unread subject:会議")

    # メール内容を解析してイベント作成
    calendar = CalendarMCPService()
    result = await calendar.create_event(
        summary="会議",
        start_time="2025-10-15T10:00:00",
        end_time="2025-10-15T11:00:00",
        description=f"メールから自動作成: {messages['content']}"
    )

    return result
```

## セキュリティ注意事項

1. **認証情報の保護**

   - `credentials.json`と`*_token.json`を`.gitignore`に追加
   - 本番環境では環境変数または秘密管理サービスを使用

2. **スコープの最小化**

   - 必要最小限のスコープのみを要求
   - 読み取り専用が十分な場合は`.readonly`スコープを使用

3. **トークンのローテーション**
   - 定期的にトークンを更新
   - 不要になったトークンは削除

## 参考リンク

- [Google Calendar API Documentation](https://developers.google.com/calendar/api)
- [OAuth 2.0 for Mobile & Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Calendar API Python Quickstart](https://developers.google.com/calendar/api/quickstart/python)
