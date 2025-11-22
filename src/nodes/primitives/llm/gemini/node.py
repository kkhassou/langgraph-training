"""LLM Node - プロバイダー注入可能なLLMノード"""

from typing import Optional
import logging
import time

from src.nodes.base import BaseNode, NodeState, NodeInput, NodeOutput
from src.core.providers.llm import LLMProvider
from src.providers.llm.gemini import GeminiProvider
from src.core.config import settings
from src.core.exceptions import (
    NodeExecutionError,
    NodeInputValidationError,
    LLMProviderError
)
from src.core.logging_config import (
    get_structured_logger,
    set_node_id,
    clear_node_id
)

logger = logging.getLogger(__name__)
structured_logger = get_structured_logger(__name__)


class LLMNode(BaseNode):
    """LLMノード（プロバイダー注入可能）
    
    依存性注入パターンを使用し、任意のLLMProviderを注入できます。
    これにより、テスト時のモック化や、異なるLLMサービスへの切り替えが容易になります。
    
    Example:
        >>> from src.providers.llm.gemini import GeminiProvider
        >>> provider = GeminiProvider(api_key="...", model="gemini-2.0-flash-exp")
        >>> node = LLMNode(provider=provider)
        >>> result = await node.execute(state)
    """

    def __init__(
        self,
        provider: LLMProvider,
        name: str = "llm_node",
        description: str = "Generate responses using LLM"
    ):
        """
        Args:
            provider: LLMプロバイダー実装
            name: ノード名
            description: ノードの説明
        """
        super().__init__(name=name, description=description)
        self.provider = provider

    async def execute(self, state: NodeState) -> NodeState:
        """LLM生成を実行
        
        Raises:
            NodeInputValidationError: 入力が不正な場合
            NodeExecutionError: ノードの実行に失敗した場合
        """
        # ノードIDを設定
        set_node_id(self.name)
        start_time = time.time()
        
        try:
            # プロンプトを取得
            if state.messages:
                prompt = state.messages[-1]
            else:
                prompt = state.data.get("prompt", "Hello, how can I help you?")
            
            if not prompt or not isinstance(prompt, str):
                raise NodeInputValidationError(
                    "Invalid prompt: must be a non-empty string",
                    details={
                        "node": self.name,
                        "prompt_type": type(prompt).__name__,
                        "messages_count": len(state.messages)
                    }
                )

            # パラメータを取得
            temperature = state.data.get("temperature", 0.7)
            max_tokens = state.data.get("max_tokens")

            # ✅ プロバイダーを通じて生成
            logger.info(f"Generating with {self.provider.__class__.__name__}")
            provider_start_time = time.time()
            response_text = await self.provider.generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            provider_duration = time.time() - provider_start_time
            
            # 構造化ロギング: プロバイダー呼び出し
            structured_logger.provider_call(
                self.provider.__class__.__name__,
                "generate",
                provider_duration,
                success=True
            )

            # 状態を更新
            state.messages.append(response_text)
            state.data["llm_response"] = response_text
            state.metadata["node"] = self.name
            state.metadata["provider"] = self.provider.__class__.__name__
            
            # 構造化ロギング: ノード実行完了
            duration = time.time() - start_time
            structured_logger.node_execute(
                self.name,
                self.__class__.__name__,
                duration,
                success=True
            )

            return state

        except NodeInputValidationError as e:
            duration = time.time() - start_time
            structured_logger.node_execute(
                self.name,
                self.__class__.__name__,
                duration,
                success=False
            )
            raise
        except LLMProviderError as e:
            duration = time.time() - start_time
            structured_logger.node_execute(
                self.name,
                self.__class__.__name__,
                duration,
                success=False
            )
            # Provider層からの例外は詳細情報を保持してNodeErrorとして再throw
            raise NodeExecutionError(
                f"LLM provider error in node {self.name}",
                details={
                    "node": self.name,
                    "provider": type(self.provider).__name__,
                    "error_details": e.details if hasattr(e, 'details') else {}
                },
                original_error=e
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Unexpected error in LLM node {self.name}: {e}")
            structured_logger.node_execute(
                self.name,
                self.__class__.__name__,
                duration,
                success=False
            )
            raise NodeExecutionError(
                f"Unexpected error in LLM node {self.name}",
                details={
                    "node": self.name,
                    "provider": type(self.provider).__name__,
                    "error_type": type(e).__name__
                },
                original_error=e
            )
        finally:
            # ノードIDをクリア
            clear_node_id()


# ✅ 後方互換性のためのエイリアス
class GeminiNode(LLMNode):
    """Geminiノード（後方互換性）
    
    ⚠️ 非推奨: 新しいコードでは LLMNode(provider=GeminiProvider(...)) を使用してください
    
    既存のコードとの互換性を保つため、このクラスは維持されていますが、
    内部的には LLMNode + GeminiProvider を使用しています。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash-exp"
    ):
        """
        Args:
            api_key: Gemini APIキー（省略時は設定から取得）
            model: 使用するモデル名
        """
        provider = GeminiProvider(
            api_key=api_key or settings.gemini_api_key,
            model=model
        )
        super().__init__(
            provider=provider,
            name="gemini_llm",
            description="Generate responses using Google Gemini LLM"
        )


class LLMInput(NodeInput):
    """Input model for LLM node"""
    prompt: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None


class LLMOutput(NodeOutput):
    """Output model for LLM node"""
    pass


# ✅ 後方互換性のためのエイリアス
class GeminiInput(LLMInput):
    """Gemini node input (deprecated, use LLMInput)"""
    max_tokens: int = 1000


class GeminiOutput(LLMOutput):
    """Gemini node output (deprecated, use LLMOutput)"""
    pass


async def llm_node_handler(input_data: LLMInput, provider: Optional[LLMProvider] = None) -> LLMOutput:
    """汎用LLMノードハンドラー
    
    Args:
        input_data: 入力データ
        provider: LLMプロバイダー（省略時はGeminiProvider）
    """
    try:
        # プロバイダーが指定されていない場合はデフォルトを使用
        if provider is None:
            provider = GeminiProvider(
                api_key=settings.gemini_api_key,
                model="gemini-2.0-flash-exp"
            )
        
        node = LLMNode(provider=provider)
        state = NodeState()
        state.messages = [input_data.prompt]
        state.data["temperature"] = input_data.temperature
        if input_data.max_tokens:
            state.data["max_tokens"] = input_data.max_tokens

        result_state = await node.execute(state)

        if "error" in result_state.data:
            return LLMOutput(
                output_text="",
                success=False,
                error_message=result_state.data["error"]
            )

        return LLMOutput(
            output_text=result_state.data.get("llm_response", ""),
            data=result_state.data
        )

    except Exception as e:
        return LLMOutput(
            output_text="",
            success=False,
            error_message=str(e)
        )


async def gemini_node_handler(input_data: GeminiInput) -> GeminiOutput:
    """Gemini node handler (deprecated, use llm_node_handler)
    
    後方互換性のために維持されています。
    """
    result = await llm_node_handler(input_data)
    return GeminiOutput(
        output_text=result.output_text,
        data=result.data,
        success=result.success,
        error_message=result.error_message
    )
