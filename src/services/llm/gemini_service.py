"""Gemini LLM Service - シンプルなヘルパー関数群"""

from typing import Optional, Type, Dict, Any
from pydantic import BaseModel
import google.generativeai as genai
import json
import logging

from src.core.config import settings
from .base import BaseLLMService

logger = logging.getLogger(__name__)


class GeminiService(BaseLLMService):
    """Gemini API のシンプルなヘルパーサービス"""
    
    _configured = False
    
    @classmethod
    def _ensure_configured(cls):
        """API設定を確実に行う"""
        if not cls._configured:
            if not settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY is not configured")
            genai.configure(api_key=settings.gemini_api_key)
            cls._configured = True
            logger.info("Gemini API configured successfully")
    
    @classmethod
    async def generate(
        cls,
        prompt: str,
        model: str = "gemini-2.0-flash-exp",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        シンプルなテキスト生成
        
        Args:
            prompt: 入力プロンプト
            model: 使用するモデル（デフォルト: gemini-2.0-flash-exp）
            temperature: 生成の多様性（0.0-1.0）
            max_tokens: 最大トークン数
            **kwargs: その他のGeneration Config パラメータ
        
        Returns:
            生成されたテキスト
        
        Example:
            >>> advice = await GeminiService.generate(
            ...     prompt="タスク管理のコツを教えてください",
            ...     temperature=0.7
            ... )
        """
        cls._ensure_configured()
        
        generation_config = {
            "temperature": temperature,
            **kwargs
        }
        if max_tokens:
            generation_config["max_output_tokens"] = max_tokens
        
        model_instance = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config
        )
        
        logger.info(f"Generating text with model: {model}, temperature: {temperature}")
        response = model_instance.generate_content(prompt)
        
        return response.text.strip()
    
    @classmethod
    async def generate_json(
        cls,
        prompt: str,
        schema: Type[BaseModel],
        model: str = "gemini-2.0-flash-exp",
        temperature: float = 0.7,
        **kwargs
    ) -> BaseModel:
        """
        構造化されたJSON出力を生成
        
        Args:
            prompt: 入力プロンプト
            schema: Pydanticスキーマ
            model: 使用するモデル
            temperature: 生成の多様性
            **kwargs: その他のパラメータ
        
        Returns:
            Pydanticモデルのインスタンス
        
        Example:
            >>> class TodoList(BaseModel):
            ...     todos: List[Dict[str, Any]]
            >>> 
            >>> result = await GeminiService.generate_json(
            ...     prompt="メールからTODOを抽出してください",
            ...     schema=TodoList
            ... )
        """
        cls._ensure_configured()
        
        # JSONスキーマを追加
        schema_json = schema.schema_json(indent=2)
        json_prompt = f"""{prompt}

以下のJSON形式でのみ返答してください。他の説明は一切含めないでください：
{schema_json}
"""
        
        logger.info(f"Generating JSON with schema: {schema.__name__}")
        text_response = await cls.generate(
            prompt=json_prompt,
            model=model,
            temperature=temperature,
            **kwargs
        )
        
        # マークダウンコードブロックを削除
        cleaned_response = cls._clean_json_response(text_response)
        
        # Pydanticモデルにパース
        try:
            return schema.parse_raw(cleaned_response)
        except Exception as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response was: {cleaned_response}")
            raise ValueError(f"Failed to parse LLM response as JSON: {str(e)}")
    
    @classmethod
    def _clean_json_response(cls, response: str) -> str:
        """JSONレスポンスからマークダウンコードブロックを削除"""
        cleaned = response.strip()
        
        # マークダウンコードブロックを削除
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        return cleaned.strip()
    
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
        """
        コンテキスト付きテキスト生成（RAG用）
        
        Args:
            user_query: ユーザーの質問
            context: 参考情報（検索結果など）
            system_instruction: システム命令（オプション）
            model: 使用するモデル
            temperature: 生成の多様性
            **kwargs: その他のパラメータ
        
        Returns:
            生成されたテキスト
        
        Example:
            >>> answer = await GeminiService.generate_with_context(
            ...     user_query="機械学習とは？",
            ...     context="機械学習は...（検索結果）",
            ...     system_instruction="専門家として回答してください"
            ... )
        """
        default_instruction = "以下のコンテキスト情報を参考にして、質問に答えてください。"
        instruction = system_instruction or default_instruction
        
        prompt = f"""{instruction}

コンテキスト情報:
{context}

質問: {user_query}

回答:"""
        
        return await cls.generate(
            prompt=prompt,
            model=model,
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
        """
        チャット形式での生成
        
        Args:
            messages: メッセージ履歴 [{"role": "user", "content": "..."}]
            model: 使用するモデル
            temperature: 生成の多様性
            **kwargs: その他のパラメータ
        
        Returns:
            生成されたテキスト
        
        Example:
            >>> response = await GeminiService.chat(
            ...     messages=[
            ...         {"role": "user", "content": "こんにちは"},
            ...         {"role": "assistant", "content": "こんにちは！"},
            ...         {"role": "user", "content": "今日の天気は？"}
            ...     ]
            ... )
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
        
        return await cls.generate(
            prompt=prompt,
            model=model,
            temperature=temperature,
            **kwargs
        )


# 便利な関数エイリアス（より簡潔な呼び出し用）
async def generate_text(prompt: str, **kwargs) -> str:
    """シンプルなテキスト生成のエイリアス"""
    return await GeminiService.generate(prompt, **kwargs)


async def generate_json_response(prompt: str, schema: Type[BaseModel], **kwargs) -> BaseModel:
    """JSON生成のエイリアス"""
    return await GeminiService.generate_json(prompt, schema, **kwargs)


async def generate_rag_response(user_query: str, context: str, **kwargs) -> str:
    """RAG生成のエイリアス"""
    return await GeminiService.generate_with_context(user_query, context, **kwargs)

