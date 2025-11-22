"""Gemini LLM Provider - Google Gemini APIの実装"""

from typing import Optional, Type, Dict, Any
from pydantic import BaseModel
import google.generativeai as genai
import logging

from src.core.providers.llm import LLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Gemini LLMプロバイダー実装
    
    Google Gemini APIを使用したLLMプロバイダー。
    依存性注入可能で、テスト時にモックに置き換えられます。
    
    Example:
        >>> from src.core.config import settings
        >>> provider = GeminiProvider(api_key=settings.gemini_api_key)
        >>> response = await provider.generate("Hello, AI!")
        >>> print(response)
    """
    
    def __init__(
        self, 
        api_key: str,
        model: str = "gemini-2.0-flash-exp"
    ):
        """
        Args:
            api_key: Gemini APIキー
            model: 使用するモデル名
        """
        self.api_key = api_key
        self.model = model
        
        # APIを設定
        genai.configure(api_key=api_key)
        
        logger.info(f"GeminiProvider initialized with model: {model}")
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """テキスト生成"""
        generation_config = {
            "temperature": temperature,
            **kwargs
        }
        
        if max_tokens:
            generation_config["max_output_tokens"] = max_tokens
        
        model_instance = genai.GenerativeModel(
            model_name=self.model,
            generation_config=generation_config
        )
        
        logger.info(f"Generating text with Gemini (temp: {temperature})")
        response = model_instance.generate_content(prompt)
        
        return response.text.strip()
    
    async def generate_json(
        self,
        prompt: str,
        schema: Type[BaseModel],
        temperature: float = 0.7,
        **kwargs
    ) -> BaseModel:
        """構造化されたJSON出力を生成"""
        # JSONスキーマを追加
        schema_json = schema.schema_json(indent=2)
        json_prompt = f"""{prompt}

以下のJSON形式でのみ返答してください。他の説明は一切含めないでください：
{schema_json}
"""
        
        logger.info(f"Generating JSON with schema: {schema.__name__}")
        text_response = await self.generate(
            prompt=json_prompt,
            temperature=temperature,
            **kwargs
        )
        
        # マークダウンコードブロックを削除
        cleaned_response = self._clean_json_response(text_response)
        
        # Pydanticモデルにパース
        try:
            return schema.parse_raw(cleaned_response)
        except Exception as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response was: {cleaned_response}")
            raise ValueError(f"Failed to parse LLM response as JSON: {str(e)}")
    
    async def generate_with_context(
        self,
        user_query: str,
        context: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """コンテキスト付きテキスト生成（RAG用）"""
        default_instruction = "以下のコンテキスト情報を参考にして、質問に答えてください。"
        instruction = system_instruction or default_instruction
        
        prompt = f"""{instruction}

コンテキスト情報:
{context}

質問: {user_query}

回答:"""
        
        return await self.generate(
            prompt=prompt,
            temperature=temperature,
            **kwargs
        )
    
    @staticmethod
    def _clean_json_response(response: str) -> str:
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



