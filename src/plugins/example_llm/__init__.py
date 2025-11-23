"""Example LLM Provider Plugin

これはプラグインシステムのデモ用サンプルプラグインです。
実際のAPI呼び出しは行わず、固定の応答を返します。

Usage:
    >>> from src.core.factory import ProviderFactory
    >>> provider = ProviderFactory.create_llm_provider("example_llm", {
    ...     "api_key": "demo-key",
    ...     "model": "example-model"
    ... })
    >>> response = await provider.generate("Hello")
"""

from typing import Optional, Type
from pydantic import BaseModel
import logging

from src.core.providers.llm import LLMProvider
from src.core.plugin_loader import PluginMetadata

logger = logging.getLogger(__name__)


class ExampleLLMProvider(LLMProvider):
    """サンプルLLMプロバイダー
    
    実際のAPI呼び出しは行わず、デモ用の固定応答を返します。
    プラグインの動作確認やテストに使用できます。
    
    Attributes:
        api_key: APIキー（デモ用）
        model: モデル名（デモ用）
        responses: カスタム応答の辞書
    
    Example:
        >>> provider = ExampleLLMProvider(
        ...     api_key="demo-key",
        ...     model="example-model",
        ...     responses={"Hello": "Hi there!"}
        ... )
        >>> result = await provider.generate("Hello")
        >>> print(result)  # "Hi there!"
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "example-model-v1",
        responses: Optional[dict] = None
    ):
        """
        Args:
            api_key: APIキー（デモ用、実際には使用されない）
            model: モデル名（デモ用）
            responses: カスタム応答の辞書（キー: プロンプト、値: 応答）
        """
        self.api_key = api_key
        self.model = model
        self.responses = responses or {}
        
        logger.info(
            f"ExampleLLMProvider initialized with model: {model}"
        )
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """テキスト生成（デモ用固定応答）
        
        Args:
            prompt: 入力プロンプト
            temperature: 温度パラメータ（デモ用、実際には使用されない）
            max_tokens: 最大トークン数（デモ用、実際には使用されない）
            **kwargs: その他のパラメータ
        
        Returns:
            生成されたテキスト（固定応答）
        """
        logger.info(f"ExampleLLMProvider.generate called with prompt: {prompt[:50]}...")
        
        # カスタム応答があれば使用
        if prompt in self.responses:
            return self.responses[prompt]
        
        # デフォルト応答
        return (
            f"[Example LLM Response]\n"
            f"Model: {self.model}\n"
            f"Prompt: {prompt}\n"
            f"Temperature: {temperature}\n"
            f"This is a sample response from the Example LLM Provider plugin."
        )
    
    async def generate_json(
        self,
        prompt: str,
        schema: Type[BaseModel],
        temperature: float = 0.7,
        **kwargs
    ) -> BaseModel:
        """JSON生成（デモ用）
        
        Args:
            prompt: 入力プロンプト
            schema: Pydanticスキーマ
            temperature: 温度パラメータ
            **kwargs: その他のパラメータ
        
        Returns:
            Pydanticモデルのインスタンス
        """
        logger.info(f"ExampleLLMProvider.generate_json called with schema: {schema.__name__}")
        
        # スキーマのフィールドからデフォルト値を作成
        default_values = {}
        for field_name, field_info in schema.model_fields.items():
            # フィールドのデフォルト値または型に応じたデフォルト
            if field_info.default is not None:
                default_values[field_name] = field_info.default
            elif field_info.annotation == str:
                default_values[field_name] = f"example_{field_name}"
            elif field_info.annotation == int:
                default_values[field_name] = 0
            elif field_info.annotation == float:
                default_values[field_name] = 0.0
            elif field_info.annotation == bool:
                default_values[field_name] = True
            else:
                default_values[field_name] = None
        
        return schema(**default_values)
    
    async def generate_with_context(
        self,
        user_query: str,
        context: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """コンテキスト付きテキスト生成（デモ用）
        
        Args:
            user_query: ユーザーの質問
            context: コンテキスト情報
            system_instruction: システム指示
            temperature: 温度パラメータ
            **kwargs: その他のパラメータ
        
        Returns:
            生成されたテキスト
        """
        logger.info(f"ExampleLLMProvider.generate_with_context called with query: {user_query[:50]}...")
        
        return (
            f"[Example LLM Response with Context]\n"
            f"Model: {self.model}\n"
            f"Query: {user_query}\n"
            f"Context Length: {len(context)} characters\n"
            f"System Instruction: {system_instruction or 'None'}\n"
            f"This is a sample context-aware response."
        )


# ============================================================================
# Plugin Metadata (Required)
# ============================================================================

plugin_metadata = PluginMetadata(
    name="example_llm",
    version="1.0.0",
    author="LangGraph Training Team",
    description="Example LLM Provider for demonstration and testing",
    provider_type="llm",
    enabled=True,
    dependencies=[]  # No external dependencies
)

