"""RAG Service - 検索拡張生成の統合サービス"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from src.infrastructure.embeddings.gemini import GeminiEmbeddingProvider
from src.infrastructure.vector_stores.supabase import SupabaseVectorStore
from src.infrastructure.vector_stores.local import LocalVectorStore
from src.infrastructure.vector_stores.base import Document
from src.services.llm.gemini_service import GeminiService
from src.core.config import settings

logger = logging.getLogger(__name__)


class RAGResult(BaseModel):
    """RAG実行結果"""
    answer: str
    retrieved_documents: List[Dict[str, Any]]
    query_embedding: Optional[List[float]] = None
    context_used: str


class RAGService:
    """RAG (Retrieval-Augmented Generation) サービス
    
    embedding生成、検索、LLM生成を統合したワンストップサービス
    """
    
    def __init__(self):
        self.embedding_provider = None
        self.vector_store = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """コンポーネントの初期化"""
        if self._initialized:
            return
        
        # Embedding Provider
        if self.embedding_provider is None:
            self.embedding_provider = GeminiEmbeddingProvider(
                model_name=settings.gemini_embedding_model,
                dimension=settings.embedding_dimension
            )
            logger.info("Embedding provider initialized")
        
        # Vector Store
        if self.vector_store is None:
            try:
                if settings.supabase_url and settings.supabase_key:
                    self.vector_store = SupabaseVectorStore(
                        dimension=settings.embedding_dimension
                    )
                    logger.info("Using Supabase vector store")
                else:
                    raise ValueError("Supabase credentials not configured")
            except Exception as e:
                logger.warning(f"Supabase initialization failed: {str(e)}")
                logger.info("Falling back to local vector store")
                self.vector_store = LocalVectorStore(
                    dimension=settings.embedding_dimension
                )
        
        self._initialized = True
    
    async def query(
        self,
        query: str,
        collection_name: str = "default_collection",
        top_k: int = 5,
        include_embedding: bool = False,
        temperature: float = 0.7
    ) -> RAGResult:
        """
        RAGクエリを実行
        
        Args:
            query: ユーザーの質問
            collection_name: 検索対象のコレクション
            top_k: 取得するドキュメント数
            include_embedding: 埋め込みベクトルを含めるか
            temperature: LLMの温度パラメータ
        
        Returns:
            RAG実行結果
        
        Example:
            >>> service = RAGService()
            >>> result = await service.query(
            ...     query="機械学習とは？",
            ...     collection_name="tech_docs",
            ...     top_k=5
            ... )
            >>> print(result.answer)
        """
        await self._ensure_initialized()
        
        logger.info(f"RAG query: {query}")
        
        # Step 1: Generate query embedding
        query_embedding = await self.embedding_provider.embed_query(query)
        logger.debug(f"Generated query embedding (dimension: {len(query_embedding)})")
        
        # Step 2: Retrieve relevant documents
        search_results = await self.vector_store.search(
            collection_name=collection_name,
            query_embedding=query_embedding,
            top_k=top_k
        )
        logger.info(f"Retrieved {len(search_results)} documents")
        
        # Step 3: Prepare context
        context_parts = []
        retrieved_docs = []
        
        for result in search_results:
            context_parts.append(f"文書{result.rank + 1}: {result.document.content}")
            retrieved_docs.append({
                "id": result.document.id,
                "content": result.document.content,
                "metadata": result.document.metadata,
                "score": result.score,
                "rank": result.rank
            })
        
        context = "\n\n".join(context_parts)
        
        # Step 4: Generate answer using LLM
        answer = await GeminiService.generate_with_context(
            user_query=query,
            context=context,
            system_instruction="あなたは質問応答システムです。文脈情報に基づいて正確に答え、情報が不足している場合は明確に述べてください。",
            temperature=temperature
        )
        
        logger.info("Generated RAG answer")
        
        return RAGResult(
            answer=answer,
            retrieved_documents=retrieved_docs,
            query_embedding=query_embedding if include_embedding else None,
            context_used=context
        )
    
    async def ingest_documents(
        self,
        documents: List[Dict[str, Any]],
        collection_name: str = "default_collection"
    ) -> Dict[str, Any]:
        """
        ドキュメントをVector Storeに登録
        
        Args:
            documents: ドキュメントのリスト
            collection_name: コレクション名
        
        Returns:
            登録結果
        """
        await self._ensure_initialized()
        
        logger.info(f"Ingesting {len(documents)} documents to {collection_name}")
        
        # Documentsオブジェクトに変換
        doc_objects = []
        for doc_data in documents:
            # Embeddingを生成
            content = doc_data.get("content", "")
            embedding = await self.embedding_provider.embed_text(content)
            
            doc = Document(
                id=doc_data.get("id", ""),
                content=content,
                metadata=doc_data.get("metadata", {}),
                embedding=embedding
            )
            doc_objects.append(doc)
        
        # Vector Storeに登録
        await self.vector_store.add_documents(
            collection_name=collection_name,
            documents=doc_objects
        )
        
        logger.info(f"Successfully ingested {len(doc_objects)} documents")
        
        return {
            "success": True,
            "count": len(doc_objects),
            "collection_name": collection_name
        }


# グローバルインスタンス（シングルトン）
_rag_service_instance: Optional[RAGService] = None


async def get_rag_service() -> RAGService:
    """RAGサービスのシングルトンインスタンスを取得"""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
        await _rag_service_instance._ensure_initialized()
    return _rag_service_instance


# 便利な関数エイリアス
async def rag_query(query: str, **kwargs) -> RAGResult:
    """RAGクエリのエイリアス"""
    service = await get_rag_service()
    return await service.query(query, **kwargs)


async def ingest_documents(documents: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
    """ドキュメント登録のエイリアス"""
    service = await get_rag_service()
    return await service.ingest_documents(documents, **kwargs)

