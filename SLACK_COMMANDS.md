# Slack Slash Commands 実装ガイド

## 概要

このドキュメントでは、Slack Slash Commandsの実装内容と使い方を説明します。

## エンドポイント構成

### 1. 汎用デバッグエンドポイント
**URL**: `/slack/commands`
**用途**: 全てのSlackコマンドからのデータを受信し、そのまま返す

```bash
# テスト例
curl -X POST http://localhost:8001/slack/commands \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "token=test&team_id=T123&user_name=kouichi&command=/test&text=hello"
```

**レスポンス例**:
```json
{
  "response_type": "ephemeral",
  "text": "コマンドを受信しました: /test",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "✅ *コマンド実行*: `/test`"
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "📥 *受信したデータ:*\n\n• *token*: `testtoken1...`\n• *user_name*: `kouichi`\n..."
      }
    }
  ]
}
```

### 2. TODO専用エンドポイント
**URL**: `/slack/cmd/todo`
**用途**: TODOワークフローを実行し、結果をSlackに返す

**処理フロー**:
1. 即座にレスポンス（3秒以内）: "🔄 TODOワークフローを開始しています..."
2. バックグラウンドでワークフロー実行
3. 完了後、`response_url`に結果を送信

**Slackでの使用例**:
```
/todo 1. POSTMANのトークン問題解消 2. ハンズオンの式次第と手順書の作成 3. Slackのチャンネル制限の調査
```

**処理内容**:
- テキストをGemini LLMで解析してTODO抽出
- 各TODOに対して並列でアドバイス生成
- Slack Block Kitで整形して表示

### 3. ヘルプエンドポイント
**URL**: `/slack/cmd/help`
**用途**: 利用可能なコマンドの説明を表示

### 4. デバッグエンドポイント
**URL**: `/slack/cmd/debug`
**用途**: 受信データを整形して表示（開発時のデバッグ用）

## Slackからのデータ構造

Slackは `application/x-www-form-urlencoded` 形式でデータを送信します:

```
token=xxxxxx
team_id=T123
team_domain=example
channel_id=C456
channel_name=general
user_id=U789
user_name=kouichi
command=/todo
text=hello world
response_url=https://hooks.slack.com/commands/...
trigger_id=123456.abcdef
```

### パラメータ説明

| パラメータ | 説明 | 例 |
|-----------|------|-----|
| `token` | 検証トークン（非推奨、署名検証を使用） | `xoxb-...` |
| `team_id` | ワークスペースID | `T123456` |
| `team_domain` | ワークスペースドメイン | `mycompany` |
| `channel_id` | コマンド実行チャンネルID | `C123456` |
| `channel_name` | チャンネル名 | `general` |
| `user_id` | 実行ユーザーID | `U123456` |
| `user_name` | ユーザー名 | `kouichi` |
| `command` | 実行されたコマンド | `/todo` |
| `text` | コマンド後のテキスト | `タスク内容` |
| `response_url` | 遅延レスポンス用URL | `https://hooks.slack.com/...` |
| `trigger_id` | モーダル開封用ID | `123456.abcdef` |

## レスポンスタイプ

### 1. Ephemeral（実行者のみ表示）

```python
{
    "response_type": "ephemeral",
    "text": "これはあなただけに見えます"
}
```

### 2. In Channel（全員に表示）

```python
{
    "response_type": "in_channel",
    "text": "これはチャンネル全員に見えます"
}
```

## Slack Block Kit

リッチなUIを作成するためのBlock Kit使用例:

```python
{
    "response_type": "ephemeral",
    "blocks": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*太字* _イタリック_ `コード`"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "補足情報"
                }
            ]
        }
    ]
}
```

## 遅延レスポンス（Response URL）

Slackのコマンドは3秒以内にレスポンスが必要です。
時間がかかる処理は、バックグラウンドで実行し、`response_url`に結果を送信します。

```python
import httpx

async def send_delayed_response(response_url: str, message: dict):
    async with httpx.AsyncClient() as client:
        await client.post(response_url, json=message)
```

**使用例** (`/slack/cmd/todo`):
1. 即座に「処理中...」を返す
2. BackgroundTasksでワークフロー実行
3. 完了後、response_urlに結果を送信

## TODOワークフローの実行フロー

```
┌─────────────────┐
│ Slack: /todo    │
│ テキスト入力    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ 1. 即座にレスポンス      │
│    "処理中..."          │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 2. BackgroundTask起動   │
│    ワークフロー実行      │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 3. Gemini LLMで解析     │
│    TODO抽出             │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 4. 各TODOにアドバイス   │
│    並列処理             │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 5. 結果を整形           │
│    Slack Block Kit      │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 6. response_urlに送信   │
│    チャンネルに表示     │
└─────────────────────────┘
```

## ローカルテスト

### 1. デバッグエンドポイント

```bash
curl -X POST http://localhost:8001/slack/commands \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "token=test&team_id=T123&team_domain=example&channel_id=C456&channel_name=general&user_id=U789&user_name=kouichi&command=/debug&text=test&response_url=https://example.com&trigger_id=123"
```

### 2. TODOコマンド

```bash
curl -X POST http://localhost:8001/slack/cmd/todo \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "user_name=kouichi&user_id=U123&channel_name=general&text=1. タスク1 2. タスク2&response_url=https://example.com"
```

### 3. ヘルプコマンド

```bash
curl -X POST http://localhost:8001/slack/cmd/help \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "command=/help"
```

## Slackアプリ設定

### Slash Commandsの追加

1. https://api.slack.com/apps → Your App
2. "Slash Commands" → "Create New Command"

**TODOコマンド設定**:
- Command: `/todo`
- Request URL: `https://your-app.onrender.com/slack/cmd/todo`
- Short Description: `TODOワークフローを実行`
- Usage Hint: `[タスク内容]`

**デバッグコマンド設定**:
- Command: `/debug`
- Request URL: `https://your-app.onrender.com/slack/cmd/debug`
- Short Description: `デバッグ情報を表示`

3. "Install App" → "Reinstall to Workspace"（新しいコマンド追加後）

## トラブルシューティング

### コマンドが応答しない

**症状**: `/todo` を実行してもSlackに何も表示されない

**確認事項**:
1. Renderのログを確認: `Logs` タブ
2. エンドポイントが正しいか確認
3. アプリが再インストールされているか確認

### 3秒タイムアウト

**症状**: "timeout" エラー

**原因**: Slackは3秒以内にレスポンスが必要

**解決**:
- 即座にレスポンスを返す
- 重い処理はBackgroundTasksで実行
- response_urlで遅延レスポンス送信

### Block Kit表示エラー

**症状**: ブロックが正しく表示されない

**確認**:
- Block Kit Builder でテスト: https://app.slack.com/block-kit-builder
- JSON構造が正しいか確認
- `type`、`text`、`mrkdwn` の指定を確認

## 拡張例

### 新しいコマンドの追加

```python
@router.post("/mycommand")
async def handle_my_command(request: Request):
    form_data = await request.form()
    text = form_data.get("text", "")

    # カスタム処理
    result = process_my_command(text)

    return {
        "response_type": "ephemeral",
        "text": f"処理結果: {result}"
    }
```

### インタラクティブボタンの追加

```python
{
    "blocks": [
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "承認"
                    },
                    "action_id": "approve_button",
                    "value": "approve"
                }
            ]
        }
    ]
}
```

ボタンクリック時は `/slack/interactions` で処理されます。

## まとめ

- `/slack/commands` - 汎用デバッグエンドポイント
- `/slack/cmd/todo` - TODOワークフロー実行
- `/slack/cmd/help` - ヘルプ表示
- `/slack/cmd/debug` - デバッグ情報表示

全てのエンドポイントは `application/x-www-form-urlencoded` でデータを受け取り、
Slack Block Kit形式でリッチなレスポンスを返します。

詳細なデプロイ手順は `DEPLOY.md` を参照してください。
