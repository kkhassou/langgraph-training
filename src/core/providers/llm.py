"""LLM Provider Interface - LLMプロバイダーの抽象インターフェース"""

from abc import ABC, abstractmethod
from typing import Optional, Type, Dict, Any
from pydantic import BaseModel


class LLMProvider(ABC):
    """LLMプロバイダーの抽象インターフェース
    
    このインターフェースを実装することで、異なるLLMサービス
    （Gemini, OpenAI, Anthropicなど）を統一的に扱えます。
    
    Example:
        >>> provider = GeminiProvider(api_key="...")
        >>> response = await provider.generate("Hello!")
        >>> print(response)
    """
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """テキスト生成
        
        Args:
            prompt: 入力プロンプト
            temperature: 生成の多様性（0.0-1.0、高いほど多様）
            max_tokens: 最大生成トークン数
            **kwargs: その他のモデル固有パラメータ
        
        Returns:
            生成されたテキスト
        
        Raises:
            Exception: 生成に失敗した場合
        """
        pass
    
    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        schema: Type[BaseModel],
        temperature: float = 0.7,
        **kwargs
    ) -> BaseModel:
        """構造化されたJSON出力を生成
        
        Args:
            prompt: 入力プロンプト
            schema: Pydanticスキーマ（出力の型定義）
            temperature: 生成の多様性
            **kwargs: その他のパラメータ
        
        Returns:
            Pydanticモデルのインスタンス
        
        Raises:
            ValueError: JSONのパースに失敗した場合
            Exception: 生成に失敗した場合
        
        Example:
            >>> class TodoItem(BaseModel):
            ...     title: str
            ...     priority: str
            >>> 
            >>> result = await provider.generate_json(
            ...     "TODOを作成してください",
            ...     schema=TodoItem
            ... )
            >>> print(result.title)
        """
        pass
    
    @abstractmethod
    async def generate_with_context(
        self,
        user_query: str,
        context: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """コンテキスト付きテキスト生成（RAG用）
        
        Args:
            user_query: ユーザーの質問
            context: 参考情報（検索結果、ドキュメントなど）
            system_instruction: システム命令（オプション）
            temperature: 生成の多様性
            **kwargs: その他のパラメータ
        
        Returns:
            生成されたテキスト
        
        Example:
            >>> answer = await provider.generate_with_context(
            ...     user_query="機械学習とは？",
            ...     context="機械学習はAIの一分野で...",
            ...     system_instruction="専門家として回答してください"
            ... )
        """
        pass



