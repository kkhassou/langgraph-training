"""Provider Factory - プロバイダーの生成を管理するファクトリー"""

from typing import Dict, Any, Optional, Type
import logging

from src.core.providers.llm import LLMProvider
from src.core.providers.rag import RAGProvider
from src.providers.llm.gemini import GeminiProvider
from src.providers.llm.mock import MockLLMProvider
from src.providers.rag.simple import SimpleRAGProvider
from src.core.config import settings
from src.core.exceptions import (
    UnknownProviderError,
    ProviderRegistrationError,
    MissingConfigError
)

logger = logging.getLogger(__name__)


class ProviderFactory:
    """プロバイダーファクトリー（軽量版）
    
    各種プロバイダーの生成を一元管理します。
    設定ベースでプロバイダーを生成でき、新しいプロバイダーの登録も可能です。
    
    Example:
        >>> # デフォルト設定で生成
        >>> provider = ProviderFactory.create_llm_provider()
        >>> 
        >>> # カスタム設定で生成
        >>> provider = ProviderFactory.create_llm_provider(
        ...     provider_type="gemini",
        ...     config={"model": "gemini-pro"}
        ... )
        >>> 
        >>> # 新しいプロバイダーを登録
        >>> ProviderFactory.register_llm_provider("openai", OpenAIProvider)
    """

    # プロバイダーレジストリ
    _llm_providers: Dict[str, Type[LLMProvider]] = {
        "gemini": GeminiProvider,
        "mock": MockLLMProvider,
    }
    
    _rag_providers: Dict[str, Type[RAGProvider]] = {
        "simple": SimpleRAGProvider,
    }

    @classmethod
    def create_llm_provider(
        cls,
        provider_type: str = "gemini",
        config: Optional[Dict[str, Any]] = None
    ) -> LLMProvider:
        """LLMプロバイダーを生成
        
        Args:
            provider_type: プロバイダータイプ（"gemini", "mock"など）
            config: プロバイダー固有の設定
        
        Returns:
            LLMProvider: 生成されたプロバイダー
        
        Raises:
            UnknownProviderError: 未知のプロバイダータイプの場合
            MissingConfigError: 必須設定が欠落している場合
        
        Example:
            >>> # デフォルト（Gemini）
            >>> provider = ProviderFactory.create_llm_provider()
            >>> 
            >>> # モックプロバイダー
            >>> provider = ProviderFactory.create_llm_provider(
            ...     provider_type="mock",
            ...     config={"default_response": "Test response"}
            ... )
        """
        if provider_type not in cls._llm_providers:
            available = ", ".join(cls._llm_providers.keys())
            raise UnknownProviderError(
                f"Unknown LLM provider type: {provider_type}",
                details={
                    "provider_type": provider_type,
                    "available_providers": list(cls._llm_providers.keys())
                }
            )

        provider_class = cls._llm_providers[provider_type]
        config = config or {}

        # デフォルト設定を適用
        if provider_type == "gemini":
            if "api_key" not in config:
                if not settings.gemini_api_key:
                    raise MissingConfigError(
                        "GEMINI_API_KEY is not configured",
                        details={
                            "provider_type": provider_type,
                            "missing_config": "GEMINI_API_KEY",
                            "hint": "Set GEMINI_API_KEY in .env file or pass api_key in config"
                        }
                    )
                config["api_key"] = settings.gemini_api_key
            if "model" not in config:
                config["model"] = "gemini-2.0-flash-exp"

        logger.info(f"Creating LLM provider: {provider_type}")
        try:
            return provider_class(**config)
        except Exception as e:
            raise ProviderRegistrationError(
                f"Failed to create {provider_type} provider",
                details={
                    "provider_type": provider_type,
                    "provider_class": provider_class.__name__,
                    "config_keys": list(config.keys())
                },
                original_error=e
            )
    
    @classmethod
    def create_rag_provider(
        cls,
        provider_type: str = "simple",
        config: Optional[Dict[str, Any]] = None
    ) -> RAGProvider:
        """RAGプロバイダーを生成
        
        Args:
            provider_type: プロバイダータイプ（"simple"など）
            config: プロバイダー固有の設定
        
        Returns:
            RAGProvider: 生成されたプロバイダー
        
        Raises:
            UnknownProviderError: 未知のプロバイダータイプの場合
            ProviderRegistrationError: プロバイダーの生成に失敗した場合
        
        Example:
            >>> provider = ProviderFactory.create_rag_provider()
        """
        if provider_type not in cls._rag_providers:
            available = ", ".join(cls._rag_providers.keys())
            raise UnknownProviderError(
                f"Unknown RAG provider type: {provider_type}",
                details={
                    "provider_type": provider_type,
                    "available_providers": list(cls._rag_providers.keys())
                }
            )

        provider_class = cls._rag_providers[provider_type]
        config = config or {}

        logger.info(f"Creating RAG provider: {provider_type}")
        try:
            return provider_class(**config)
        except Exception as e:
            raise ProviderRegistrationError(
                f"Failed to create {provider_type} RAG provider",
                details={
                    "provider_type": provider_type,
                    "provider_class": provider_class.__name__,
                    "config_keys": list(config.keys())
                },
                original_error=e
            )

    @classmethod
    def register_llm_provider(
        cls,
        name: str,
        provider_class: Type[LLMProvider]
    ):
        """新しいLLMプロバイダーを登録（拡張用）
        
        Args:
            name: プロバイダー名
            provider_class: プロバイダークラス
        
        Example:
            >>> class CustomProvider(LLMProvider):
            ...     pass
            >>> 
            >>> ProviderFactory.register_llm_provider("custom", CustomProvider)
            >>> provider = ProviderFactory.create_llm_provider("custom")
        """
        logger.info(f"Registering LLM provider: {name}")
        cls._llm_providers[name] = provider_class
    
    @classmethod
    def register_rag_provider(
        cls,
        name: str,
        provider_class: Type[RAGProvider]
    ):
        """新しいRAGプロバイダーを登録（拡張用）
        
        Args:
            name: プロバイダー名
            provider_class: プロバイダークラス
        """
        logger.info(f"Registering RAG provider: {name}")
        cls._rag_providers[name] = provider_class

    @classmethod
    def list_llm_providers(cls) -> list[str]:
        """利用可能なLLMプロバイダーをリスト
        
        Returns:
            プロバイダー名のリスト
        """
        return list(cls._llm_providers.keys())
    
    @classmethod
    def list_rag_providers(cls) -> list[str]:
        """利用可能なRAGプロバイダーをリスト
        
        Returns:
            プロバイダー名のリスト
        """
        return list(cls._rag_providers.keys())
    
    @classmethod
    def get_default_llm_provider(cls) -> LLMProvider:
        """デフォルトのLLMプロバイダーを取得
        
        Returns:
            デフォルトのLLMプロバイダー（Gemini）
        """
        return cls.create_llm_provider(provider_type="gemini")
    
    @classmethod
    def get_default_rag_provider(cls) -> RAGProvider:
        """デフォルトのRAGプロバイダーを取得
        
        Returns:
            デフォルトのRAGプロバイダー（Simple）
        """
        return cls.create_rag_provider(provider_type="simple")


# 便利な関数エイリアス
def create_llm_provider(provider_type: str = "gemini", **kwargs) -> LLMProvider:
    """LLMプロバイダーを生成（関数版）
    
    Args:
        provider_type: プロバイダータイプ
        **kwargs: プロバイダー固有の設定
    
    Returns:
        LLMProvider: 生成されたプロバイダー
    """
    return ProviderFactory.create_llm_provider(provider_type, config=kwargs)


def create_rag_provider(provider_type: str = "simple", **kwargs) -> RAGProvider:
    """RAGプロバイダーを生成（関数版）
    
    Args:
        provider_type: プロバイダータイプ
        **kwargs: プロバイダー固有の設定
    
    Returns:
        RAGProvider: 生成されたプロバイダー
    """
    return ProviderFactory.create_rag_provider(provider_type, config=kwargs)

