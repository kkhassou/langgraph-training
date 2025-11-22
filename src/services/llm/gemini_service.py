"""Gemini LLM Service - 後方互換性レイヤー

⚠️  非推奨: このサービスは後方互換性のために残されています。
新しいコードでは src.providers.llm.gemini.GeminiProvider を使用してください。

Example (旧):
    >>> response = await GeminiService.generate("Hello")

Example (新):
    >>> from src.providers.llm.gemini import GeminiProvider
    >>> provider = GeminiProvider(api_key=settings.gemini_api_key)
    >>> response = await provider.generate("Hello")
"""

from typing import Optional, Type, Dict, Any
from pydantic import BaseModel
import logging

from src.core.config import settings
from src.providers.llm.gemini import GeminiProvider
from .base import BaseLLMService

logger = logging.getLogger(__name__)

# グローバルプロバイダーインスタンス（後方互換性用）
_default_provider: Optional[GeminiProvider] = None


def _get_default_provider() -> GeminiProvider:
    """デフォルトプロバイダーを取得（シングルトン）"""
    global _default_provider
    if _default_provider is None:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not configured")
        _default_provider = GeminiProvider(
            api_key=settings.gemini_api_key,
            model="gemini-2.0-flash-exp"
        )
        logger.info("Default GeminiProvider initialized for backward compatibility")
    return _default_provider


class GeminiService(BaseLLMService):
    """Gemini API のヘルパーサービス（後方互換性）
    
    ⚠️  非推奨: 新しいコードでは GeminiProvider を直接使用してください
    """
    
    @classmethod
    async def generate(
        cls,
        prompt: str,
        model: str = "gemini-2.0-flash-exp",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """後方互換性のためのラッパー
        
        ⚠️  非推奨: GeminiProvider.generate() を使用してください
        """
        provider = _get_default_provider()
        return await provider.generate(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    @classmethod
    async def generate_json(
        cls,
        prompt: str,
        schema: Type[BaseModel],
        model: str = "gemini-2.0-flash-exp",
        temperature: float = 0.7,
        **kwargs
    ) -> BaseModel:
        """後方互換性のためのラッパー
        
        ⚠️  非推奨: GeminiProvider.generate_json() を使用してください
        """
        provider = _get_default_provider()
        return await provider.generate_json(
            prompt=prompt,
            schema=schema,
            temperature=temperature,
            **kwargs
        )
    
    
    @classmethod
    async def generate_with_context(
        cls,
        user_query: str,
        context: str,
        system_instruction: Optional[str] = None,
        model: str = "gemini-2.0-flash-exp",
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """後方互換性のためのラッパー
        
        ⚠️  非推奨: GeminiProvider.generate_with_context() を使用してください
        """
        provider = _get_default_provider()
        return await provider.generate_with_context(
            user_query=user_query,
            context=context,
            system_instruction=system_instruction,
            temperature=temperature,
            **kwargs
        )
    
    @classmethod
    async def chat(
        cls,
        messages: list[Dict[str, str]],
        model: str = "gemini-2.0-flash-exp",
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """チャット形式での生成（後方互換性）
        
        ⚠️  非推奨: GeminiProvider.generate() を使用してください
        """
        # メッセージを単一のプロンプトに変換
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
            elif role == "system":
                prompt_parts.append(f"System: {content}")
        
        prompt = "\n\n".join(prompt_parts) + "\n\nAssistant:"
        
        provider = _get_default_provider()
        return await provider.generate(
            prompt=prompt,
            temperature=temperature,
            **kwargs
        )


# 便利な関数エイリアス（後方互換性用）
async def generate_text(prompt: str, **kwargs) -> str:
    """シンプルなテキスト生成のエイリアス
    
    ⚠️  非推奨: GeminiProvider.generate() を使用してください
    """
    return await GeminiService.generate(prompt, **kwargs)


async def generate_json_response(prompt: str, schema: Type[BaseModel], **kwargs) -> BaseModel:
    """JSON生成のエイリアス
    
    ⚠️  非推奨: GeminiProvider.generate_json() を使用してください
    """
    return await GeminiService.generate_json(prompt, schema, **kwargs)


async def generate_rag_response(user_query: str, context: str, **kwargs) -> str:
    """RAG生成のエイリアス
    
    ⚠️  非推奨: GeminiProvider.generate_with_context() を使用してください
    """
    return await GeminiService.generate_with_context(user_query, context, **kwargs)

