"""RAG Provider Interface - RAGプロバイダーの抽象インターフェース"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class RAGResult(BaseModel):
    """RAG実行結果
    
    Attributes:
        answer: LLMが生成した回答
        retrieved_documents: 検索されたドキュメントのリスト
        query_embedding: クエリの埋め込みベクトル（オプション）
        context_used: LLMに渡されたコンテキスト
    """
    answer: str = Field(..., description="生成された回答")
    retrieved_documents: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="検索されたドキュメント"
    )
    query_embedding: Optional[List[float]] = Field(
        default=None,
        description="クエリの埋め込みベクトル"
    )
    context_used: str = Field(..., description="LLMに渡されたコンテキスト")


class RAGProvider(ABC):
    """RAGプロバイダーの抽象インターフェース
    
    Retrieval-Augmented Generation（検索拡張生成）の
    統一インターフェースを提供します。
    
    Example:
        >>> provider = SimpleRAGProvider(...)
        >>> result = await provider.query(
        ...     query="機械学習とは？",
        ...     collection_name="tech_docs"
        ... )
        >>> print(result.answer)
    """
    
    @abstractmethod
    async def query(
        self,
        query: str,
        collection_name: str = "default_collection",
        top_k: int = 5,
        include_embedding: bool = False,
        temperature: float = 0.7
    ) -> RAGResult:
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
        pass
    
    @abstractmethod
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
        pass



