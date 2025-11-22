"""LLM Services Base Classes"""

from abc import ABC, abstractmethod
from typing import Optional, Type, Dict, Any
from pydantic import BaseModel


class BaseLLMService(ABC):
    """LLMサービスの基底クラス"""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        テキストを生成
        
        Args:
            prompt: 入力プロンプト
            temperature: 生成の多様性（0.0-1.0）
            max_tokens: 最大トークン数
            **kwargs: その他のモデル固有パラメータ
        
        Returns:
            生成されたテキスト
        """
        pass
    
    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        schema: Type[BaseModel],
        **kwargs
    ) -> BaseModel:
        """
        構造化されたJSON出力を生成
        
        Args:
            prompt: 入力プロンプト
            schema: Pydanticスキーマ
            **kwargs: その他のモデル固有パラメータ
        
        Returns:
            Pydanticモデルのインスタンス
        """
        pass

