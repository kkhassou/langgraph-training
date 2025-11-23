"""Simple RAG Provider - RAGServiceをベースにした基本実装"""

from typing import List, Dict, Any
import logging

from src.core.providers.rag import RAGProvider, RAGResult as CoreRAGResult
from src.services.rag.rag_service import RAGService

logger = logging.getLogger(__name__)


class SimpleRAGProvider(RAGProvider):
    """シンプルなRAGプロバイダー実装
    
    既存のRAGServiceをラップし、RAGProviderインターフェースを提供します。
    依存性注入パターンにより、テスト時にモックに置き換え可能です。
    
    Example:
        >>> provider = SimpleRAGProvider()
        >>> result = await provider.query(
        ...     query="機械学習とは？",
        ...     collection_name="tech_docs"
        ... )
        >>> print(result.answer)
    """
    
    def __init__(self):
        """RAGプロバイダーを初期化"""
        self.rag_service = RAGService()
        logger.info("SimpleRAGProvider initialized")
    
    async def query(
        self,
        query: str,
        collection_name: str = "default_collection",
        top_k: int = 5,
        include_embedding: bool = False,
        temperature: float = 0.7
    ) -> CoreRAGResult:
        """RAGクエリを実行
        
        Args:
            query: ユーザーの質問
            collection_name: 検索対象のコレクション名
            top_k: 取得するドキュメント数
            include_embedding: 埋め込みベクトルを含めるか
            temperature: LLMの温度パラメータ
        
        Returns:
            RAG実行結果
        
        Raises:
            Exception: クエリ実行に失敗した場合
        """
        logger.info(f"Executing RAG query: {query}")
        
        # RAGServiceを使用して実行
        service_result = await self.rag_service.query(
            query=query,
            collection_name=collection_name,
            top_k=top_k,
            include_embedding=include_embedding,
            temperature=temperature
        )
        
        # Core RAGResult に変換
        return CoreRAGResult(
            answer=service_result.answer,
            retrieved_documents=service_result.retrieved_documents,
            query_embedding=service_result.query_embedding,
            context_used=service_result.context_used
        )
    
    async def ingest_documents(
        self,
        documents: List[Dict[str, Any]],
        collection_name: str = "default_collection"
    ) -> Dict[str, Any]:
        """ドキュメントをVector Storeに登録
        
        Args:
            documents: ドキュメントのリスト
                各ドキュメントは以下のキーを持つ辞書:
                - id: ドキュメントID
                - content: テキストコンテンツ
                - metadata: メタデータ（オプション）
            collection_name: コレクション名
        
        Returns:
            登録結果の辞書:
                - success: 成功フラグ
                - count: 登録されたドキュメント数
                - collection_name: コレクション名
        
        Example:
            >>> documents = [
            ...     {
            ...         "id": "doc1",
            ...         "content": "機械学習は...",
            ...         "metadata": {"source": "textbook"}
            ...     }
            ... ]
            >>> result = await provider.ingest_documents(
            ...     documents,
            ...     collection_name="tech_docs"
            ... )
        """
        logger.info(f"Ingesting {len(documents)} documents to {collection_name}")
        
        return await self.rag_service.ingest_documents(
            documents=documents,
            collection_name=collection_name
        )



