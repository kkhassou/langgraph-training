# 📝 Workshop Guide

## 1. 研修の目的

このワークショップでは LangGraph を使い、再利用可能な「ノード」を組み合わせて エージェント的なワークフロー を構築する方法を学びます。
FastAPI + Swagger で API として呼び出せる形にして、実務でも応用しやすい基盤を体験します。

- LangGraph の基本概念（ノード・エッジ・グラフ）
- 部品化されたノードの使い方（LLM, Slack, Jira, PowerPoint など）
- ノードを組み合わせたグラフ構築
- Mermaid 図で構造を可視化し、議論・リファクタリング
- デザインパターン（Chain of Thought, Reflection など）の応用例

## 2. 事前準備

- Docker / Docker Compose が動作する環境
- API キー（各自用意）
  - `GEMINI_API_KEY`
  - `SLACK_TOKEN`
  - `JIRA_TOKEN`
- GitHub アカウント（リポジトリクローン用）

## 3. 起動方法

```bash
# レポジトリをクローン
git clone https://github.com/your-org/langgraph-training-repo.git
cd langgraph-training

# .env ファイルを作成（APIキーを記入）
cp .env.example .env
vim .env

# Docker 起動
docker-compose up
```

→ http://localhost:8000/docs を開くと Swagger UI から API を実行できます。

## 4. ハンズオンの流れ

### Step 1. ノード単体を動かす

- Swagger で `/nodes/gemini` を呼び出し、LLM 応答を確認
- `/nodes/ppt-ingest` で PowerPoint → テキスト変換を試す

### Step 2. ノードを組み合わせたグラフを動かす

- `/graphs/ppt-summary` に PPT ファイルを渡し、Gemini で要約
- `/graphs/slack-report` で Slack メッセージを収集 → 要約 → 出力

### Step 3. 可視化して議論する

- `scripts/generate_diagram.py` を実行
- `docs/diagrams/` に生成された Mermaid 図を確認
- 「もっとノードを分割したほうが良い？」「この処理は並列化できる？」などを議論

### Step 4. デザインパターンを試す

- `/graphs/reflection` → Reflection パターンで出力改善
- `/graphs/chain-of-thought` → CoT で推論プロセスを確認
- 実務にどう応用できるかをディスカッション

## 5. 演習課題（例）

- **課題 A**: PowerPoint を要約し、Slack に要約を投稿するグラフを作成せよ
- **課題 B**: Jira チケットを自動で作成するフローを作り、Slack 通知を追加せよ
- **課題 C**: Reflection パターンを使って要約の品質を自己改善するエージェントを構築せよ

## 6. 次のステップ

- 各自の業務に関連する「ノード」を追加する（例：社内 DB 検索ノード）
- よく使うエージェントをテンプレート化し、再利用可能にする
- 3 層構造（ノード → グラフ → パターン）への発展
