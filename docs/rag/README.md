# RAG (Retrieval-Augmented Generation) Integration

このドキュメントは、LangGraph Training プロジェクトにおけるRAG機能の統合について説明します。

## 概要

RAGシステムは、外部の知識ベースから関連情報を検索し、LLMの生成品質を向上させる技術です。このプロジェクトでは段階的な実装アプローチを採用しています。

## 実装フェーズ

### Phase 0: 準備フェーズ ✅
- **目的**: RAG機能導入の準備と既存機能への影響確認
- **内容**:
  - 依存関係調査と互換性確認
  - 環境変数設定の拡張
  - ドキュメント構造の準備
  - 既存機能の動作確認

### Phase 1: 基本インフラ構築
- **目的**: RAGシステムの基盤となるインフラを構築
- **内容**:
  - ベクトルストア（ChromaDB/FAISS）の設定
  - 埋め込みモデルの統合
  - ドキュメント処理パイプライン

### Phase 2: 検索機能実装
- **目的**: 効率的な情報検索システムの構築
- **内容**:
  - セマンティック検索の実装
  - BM25による語彙検索
  - ハイブリッド検索システム

### Phase 3: RAGノード開発
- **目的**: LangGraphワークフローにRAG機能を統合
- **内容**:
  - RAGノードの実装
  - 既存LLMノードとの連携
  - コンテキスト管理

### Phase 4: 高度な機能
- **目的**: RAGシステムの最適化と高度な機能追加
- **内容**:
  - リランキング機能
  - 動的チャンク戦略
  - パフォーマンス最適化

## 依存関係

RAGシステムの実装には以下の追加パッケージが必要です：

### 必須依存関係
- `chromadb>=0.4.18` - ローカルベクトルデータベース
- `sentence-transformers>=2.2.2` - 埋め込みモデル
- `pypdf>=3.17.1` - PDF文書処理
- `tiktoken>=0.5.2` - トークン計算

### オプション依存関係
- `faiss-cpu>=1.7.4` - 高速類似性検索
- `pinecone-client>=2.2.4` - クラウドベクトルDB
- `cohere>=4.30` - リランキングAPI

詳細は `requirements-rag.txt` を参照してください。

## 設定

RAG機能の設定は `.env` ファイルで行います。`.env.example` のRAG設定セクションを参考にしてください。

### 主要設定項目

- **EMBEDDING_MODEL**: 使用する埋め込みモデル
- **MAX_CHUNK_SIZE**: ドキュメントチャンクの最大サイズ
- **SIMILARITY_THRESHOLD**: 類似性検索の閾値
- **MAX_RETRIEVAL_RESULTS**: 検索結果の最大数

## アーキテクチャ

RAGシステムは既存のClean Architectureパターンに従って実装されます：

```
app/
├── infrastructure/
│   ├── vector_stores/     # ベクトルストア実装
│   ├── embeddings/        # 埋め込みモデル
│   └── document_loaders/  # ドキュメント読み込み
├── application/
│   ├── nodes/
│   │   └── rag_node.py    # RAGノード
│   └── services/
│       └── rag_service.py # RAG関連サービス
└── presentation/
    └── api/
        └── rag_routes.py  # RAG API エンドポイント
```

## 互換性

既存機能への影響を最小限に抑えるため、以下の点に注意しています：

1. **依存関係の競合回避**: 既存パッケージとの互換性確認済み
2. **設定の分離**: RAG固有の設定は専用セクションで管理
3. **段階的導入**: 既存機能を維持したまま新機能を追加
4. **オプショナル機能**: RAG機能は既存ワークフローの拡張として実装

## トラブルシューティング

RAG機能に関する問題は `docs/rag/troubleshooting.md` を参照してください。

## 参考資料

- [LangChain RAG Documentation](https://python.langchain.com/docs/use_cases/question_answering)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Sentence Transformers](https://www.sbert.net/)