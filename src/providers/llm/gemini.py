"""Gemini LLM Provider - Google Gemini APIの実装"""

from typing import Optional, Type, Dict, Any
from pydantic import BaseModel
import google.generativeai as genai
import logging

from src.core.providers.llm import LLMProvider
from src.core.exceptions import (
    LLMProviderError,
    LLMGenerationError,
    LLMJSONParseError,
    LLMRateLimitError,
    LLMAuthenticationError
)

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
        """テキスト生成
        
        Raises:
            LLMAuthenticationError: API認証に失敗した場合
            LLMRateLimitError: レート制限に達した場合
            LLMGenerationError: その他の生成エラー
        """
        try:
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
            
            if not response.text:
                raise LLMGenerationError(
                    "Empty response from Gemini API",
                    details={
                        "model": self.model,
                        "prompt_length": len(prompt),
                        "temperature": temperature
                    }
                )
            
            return response.text.strip()
            
        except ValueError as e:
            error_msg = str(e).lower()
            if "api" in error_msg and ("key" in error_msg or "auth" in error_msg):
                raise LLMAuthenticationError(
                    "Gemini API authentication failed",
                    details={"model": self.model},
                    original_error=e
                )
            raise LLMGenerationError(
                "Failed to generate text with Gemini",
                details={
                    "model": self.model,
                    "temperature": temperature,
                    "error_type": type(e).__name__
                },
                original_error=e
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "rate" in error_msg or "limit" in error_msg:
                raise LLMRateLimitError(
                    "Gemini API rate limit exceeded",
                    details={"model": self.model},
                    original_error=e
                )
            raise LLMGenerationError(
                "Failed to generate text with Gemini",
                details={
                    "model": self.model,
                    "temperature": temperature,
                    "error_type": type(e).__name__
                },
                original_error=e
            )
    
    async def generate_json(
        self,
        prompt: str,
        schema: Type[BaseModel],
        temperature: float = 0.7,
        **kwargs
    ) -> BaseModel:
        """構造化されたJSON出力を生成
        
        Raises:
            LLMJSONParseError: JSON パースに失敗した場合
            LLMGenerationError: 生成に失敗した場合
        """
        try:
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
                raise LLMJSONParseError(
                    f"Failed to parse LLM response as {schema.__name__}",
                    details={
                        "schema": schema.__name__,
                        "response_length": len(cleaned_response),
                        "response_preview": cleaned_response[:200] if len(cleaned_response) > 200 else cleaned_response
                    },
                    original_error=e
                )
        except LLMJSONParseError:
            raise
        except Exception as e:
            raise LLMGenerationError(
                f"Failed to generate JSON with schema {schema.__name__}",
                details={
                    "schema": schema.__name__,
                    "model": self.model
                },
                original_error=e
            )
    
    async def generate_with_context(
        self,
        user_query: str,
        context: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """コンテキスト付きテキスト生成（RAG用）
        
        Raises:
            LLMGenerationError: 生成に失敗した場合
        """
        try:
            if not user_query.strip():
                raise LLMGenerationError(
                    "User query cannot be empty",
                    details={"context_length": len(context)}
                )
            
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
        except LLMGenerationError:
            raise
        except Exception as e:
            raise LLMGenerationError(
                "Failed to generate response with context",
                details={
                    "query_length": len(user_query),
                    "context_length": len(context),
                    "model": self.model
                },
                original_error=e
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



