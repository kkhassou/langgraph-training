"""Integrations Module

外部サービスとの統合ノードを提供します。

Available integrations:
- Slack: チャンネル管理、メッセージ送受信
- GitHub: リポジトリ、Issue、Pull Request管理
- Notion: ページ、データベース管理
- Google Services:
  - Gmail: メール送受信
  - Calendar: カレンダー管理
  - Docs: ドキュメント管理
  - Sheets: スプレッドシート管理
  - Slides: プレゼンテーション管理
  - Forms: フォーム管理
  - Keep: メモ管理
  - Apps Script: スクリプト実行
  - Vertex AI: AI/ML操作
"""

__all__ = [
    "slack",
    "github",
    "notion",
    "google"
]

