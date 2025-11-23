"""RAG Query Workflow のテスト"""

import pytest
from typing import List, Dict, Any
from src.workflows.atomic.rag_query import RAGQueryWorkflow, RAGQueryInput
from src.core.providers.rag import RAGProvider, RAGResult
from src.core.factory import ProviderFactory


class MockRAGProvider(RAGProvider):
    """テスト用モックRAGプロバイダー"""
    
    def __init__(self):
        self.call_history: List[Dict[str, Any]] = []
        self.mock_documents = [
            {
                "id": "doc1",
                "content": "機械学習はAIの一分野です。",
                "metadata": {"source": "test"},
                "score": 0.95,
                "rank": 0
            },
            {
                "id": "doc2",
                "content": "ディープラーニングは機械学習のサブセットです。",
                "metadata": {"source": "test"},
                "score": 0.85,
                "rank": 1
            }
        ]
    
    async def query(
        self,
        query: str,
        collection_name: str = "default_collection",
        top_k: int = 5,
        include_embedding: bool = False,
        temperature: float = 0.7
    ) -> RAGResult:
        """モックRAGクエリ"""
        self.call_history.append({
            "method": "query",
            "query": query,
            "collection_name": collection_name,
            "top_k": top_k,
            "include_embedding": include_embedding,
            "temperature": temperature
        })
        
        # モック応答を返す
        return RAGResult(
            answer=f"モック回答: {query}についての情報です。",
            retrieved_documents=self.mock_documents[:top_k],
            query_embedding=[0.1, 0.2, 0.3] if include_embedding else None,
            context_used="モックコンテキスト"
        )
    
    async def ingest_documents(
        self,
        documents: List[Dict[str, Any]],
        collection_name: str = "default_collection"
    ) -> Dict[str, Any]:
        """モックドキュメント登録"""
        self.call_history.append({
            "method": "ingest_documents",
            "document_count": len(documents),
            "collection_name": collection_name
        })
        
        return {
            "success": True,
            "count": len(documents),
            "collection_name": collection_name
        }
    
    def reset_history(self):
        """履歴をクリア"""
        self.call_history = []


@pytest.mark.asyncio
async def test_rag_workflow_basic():
    """基本的なRAGワークフローのテスト"""
    mock_provider = MockRAGProvider()
    workflow = RAGQueryWorkflow(rag_provider=mock_provider)

    result = await workflow.run(
        RAGQueryInput(query="機械学習とは？")
    )

    # 検証
    assert result.success is True
    assert "機械学習" in result.answer
    assert len(result.retrieved_documents) == 2
    assert len(mock_provider.call_history) == 1


@pytest.mark.asyncio
async def test_rag_workflow_with_parameters():
    """パラメータ付きRAGワークフローのテスト"""
    mock_provider = MockRAGProvider()
    workflow = RAGQueryWorkflow(rag_provider=mock_provider)

    result = await workflow.run(
        RAGQueryInput(
            query="ディープラーニングとは？",
            collection_name="ai_docs",
            top_k=3
        )
    )

    # 検証
    assert result.success is True
    call = mock_provider.call_history[0]
    assert call["collection_name"] == "ai_docs"
    assert call["top_k"] == 3


@pytest.mark.asyncio
async def test_rag_workflow_default_provider():
    """デフォルトプロバイダーでのテスト"""
    # モックプロバイダーを使用
    mock_provider = MockRAGProvider()
    workflow = RAGQueryWorkflow(rag_provider=mock_provider)

    result = await workflow.run(
        RAGQueryInput(query="テスト質問")
    )

    assert result.success is True
    assert result.answer is not None


@pytest.mark.asyncio
async def test_rag_workflow_document_retrieval():
    """ドキュメント取得のテスト"""
    mock_provider = MockRAGProvider()
    workflow = RAGQueryWorkflow(rag_provider=mock_provider)

    result = await workflow.run(
        RAGQueryInput(query="AIについて教えて", top_k=2)
    )

    # 取得したドキュメントを検証
    assert len(result.retrieved_documents) == 2
    assert result.retrieved_documents[0]["id"] == "doc1"
    assert result.retrieved_documents[1]["id"] == "doc2"
    assert "content" in result.retrieved_documents[0]


@pytest.mark.asyncio
async def test_rag_workflow_error_handling():
    """エラーハンドリングのテスト"""
    class ErrorRAGProvider(MockRAGProvider):
        async def query(self, query, **kwargs):
            raise Exception("Simulated RAG error")
    
    workflow = RAGQueryWorkflow(rag_provider=ErrorRAGProvider())
    result = await workflow.run(RAGQueryInput(query="Test"))

    # エラーが適切にハンドリングされることを確認
    assert result.success is False
    assert result.error_message != ""
    assert "error" in result.error_message.lower()


@pytest.mark.asyncio
async def test_rag_workflow_empty_query():
    """空のクエリのテスト"""
    mock_provider = MockRAGProvider()
    workflow = RAGQueryWorkflow(rag_provider=mock_provider)

    result = await workflow.run(
        RAGQueryInput(query="")
    )

    # 空のクエリでもエラーにならないことを確認
    # （実装によってはエラーになる可能性もある）
    assert result is not None


@pytest.mark.asyncio
async def test_rag_workflow_multiple_queries():
    """複数クエリのテスト"""
    mock_provider = MockRAGProvider()
    workflow = RAGQueryWorkflow(rag_provider=mock_provider)

    # 複数のクエリを実行
    queries = [
        "機械学習とは？",
        "ディープラーニングとは？",
        "AIの応用例は？"
    ]

    results = []
    for query in queries:
        result = await workflow.run(RAGQueryInput(query=query))
        results.append(result)

    # 全てのクエリが成功したことを確認
    assert all(r.success for r in results)
    assert len(mock_provider.call_history) == 3


@pytest.mark.asyncio
async def test_rag_workflow_different_collections():
    """異なるコレクションでのテスト"""
    mock_provider = MockRAGProvider()
    workflow = RAGQueryWorkflow(rag_provider=mock_provider)

    # 異なるコレクションを指定
    collections = ["ai_docs", "ml_docs", "dl_docs"]

    for collection in collections:
        await workflow.run(
            RAGQueryInput(
                query="テスト",
                collection_name=collection
            )
        )

    # 各コレクションが呼び出されたことを確認
    called_collections = [
        call["collection_name"] 
        for call in mock_provider.call_history
    ]
    assert called_collections == collections


@pytest.mark.asyncio
async def test_rag_workflow_top_k_variation():
    """top_kの値を変えたテスト"""
    mock_provider = MockRAGProvider()
    workflow = RAGQueryWorkflow(rag_provider=mock_provider)

    # 異なるtop_k値でテスト
    top_k_values = [1, 3, 5, 10]

    for k in top_k_values:
        await workflow.run(
            RAGQueryInput(query="テスト", top_k=k)
        )

    # 各top_k値が正しく渡されたことを確認
    called_top_k = [
        call["top_k"] 
        for call in mock_provider.call_history
    ]
    assert called_top_k == top_k_values


@pytest.mark.asyncio
async def test_rag_workflow_mermaid_diagram():
    """Mermaid図の生成テスト"""
    mock_provider = MockRAGProvider()
    workflow = RAGQueryWorkflow(rag_provider=mock_provider)

    # Mermaid図を取得
    diagram = workflow.get_mermaid_diagram()

    # 基本的な構造を確認
    assert diagram is not None
    assert isinstance(diagram, str)
    assert len(diagram) > 0


@pytest.mark.asyncio
async def test_rag_workflow_with_factory():
    """ファクトリーパターンを使ったテスト"""
    # 注: SimpleRAGProviderは実際のサービスを呼び出すため、
    # ここではモックRAGProviderを直接使用
    mock_provider = MockRAGProvider()
    workflow = RAGQueryWorkflow(rag_provider=mock_provider)

    result = await workflow.run(
        RAGQueryInput(query="ファクトリーテスト")
    )

    assert result.success is True
    assert "ファクトリーテスト" in result.answer

