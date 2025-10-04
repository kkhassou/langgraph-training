# Known Issues - Phase 0

## LangGraph Workflow Issue

### Problem
LangGraphワークフロー（例: simple-chat）でKeyError: '__start__'が発生する問題があります。

### Error Details
```
KeyError: '__start__' - Traceback (most recent call last):
  File "app/graphs/simple_chat.py", line 62, in run
    result = await self.graph.ainvoke(initial_state)
  File "langgraph/pregel/__init__.py", line 1504, in ainvoke
    async for chunk in self.astream(
  File "langgraph/pregel/__init__.py", line 1242, in astream
    next_checkpoint, next_tasks = _prepare_next_tasks(
  File "langgraph/pregel/__init__.py", line 1762, in _prepare_next_tasks
    seen = checkpoint["versions_seen"][name]
KeyError: '__start__'
```

### Affected Components
- `/graphs/simple-chat` エンドポイント
- その他のLangGraphベースのワークフロー

### Working Components
以下のコンポーネントは正常に動作しています：

✅ **個別ノード**
- `/nodes/gemini` - Gemini LLM: 正常動作
- `/nodes/` - ノード一覧: 正常動作
- `/graphs/` - グラフ一覧: 正常動作
- `/health` - ヘルスチェック: 正常動作

### Root Cause Analysis
- LangGraphのチェックポイント管理の問題
- StateGraphの初期化または状態管理の問題
- LangGraphバージョンとの互換性問題の可能性

### Attempted Fixes
1. `workflow.set_entry_point("gemini")` から `workflow.add_edge(START, "gemini")` への変更
2. 結果アクセス方法の修正（dictionary vs NodeState）
3. 例外処理の改善

### Status
- **影響度**: 中程度（個別ノードは動作、ワークフローのみ影響）
- **優先度**: Phase 1での修正を推奨
- **回避策**: 個別ノードAPIを使用

### Next Steps
1. LangGraphのバージョン確認と更新
2. 最新のLangGraph APIに合わせたコード修正
3. より単純なワークフロー例での検証

## Impact on RAG Implementation

この問題はRAG機能の実装には直接影響しません：

- **Phase 0**: 準備フェーズは完了可能（依存関係、設定、ドキュメント）
- **Phase 1**: 基本インフラは個別ノードベースで構築可能
- **Phase 2+**: LangGraphワークフロー修正後に高度な機能を実装

## Mitigation Strategy

RAG実装は以下のアプローチで進行可能：

1. **個別ノードアプローチ**: RAG機能を個別ノードとして実装
2. **API組み合わせ**: フロントエンドまたは外部オーケストレーションでノードを組み合わせ
3. **段階的修正**: LangGraph問題の解決と並行してRAG機能を開発