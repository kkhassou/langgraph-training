"""LLM Node - 汎用LLM生成ノード

このノード1つで、あらゆるLLMタスクに対応：
- 要約
- 翻訳
- 会話
- 分析
- コード生成

プロバイダー注入により、どのLLMサービスでも使用可能です。
"""

from typing import Optional
import logging
import time

from src.nodes.base import BaseNode, NodeState, NodeInput, NodeOutput
from src.core.providers.llm import LLMProvider
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
    """汎用LLMノード（プロバイダー注入可能）
    
    State入力:
        - messages: プロンプトのリスト（最後の要素を使用）
        - data["prompt"]: 代替プロンプト（messagesがない場合）
        - data["temperature"]: 生成温度（default: 0.7）
        - data["max_tokens"]: 最大トークン数（optional）
        - data["system_prompt"]: システムプロンプト（optional）
    
    State出力:
        - messages: LLM応答を追加
        - data["llm_response"]: 生成されたテキスト
        - metadata["llm_tokens"]: 使用トークン数（プロバイダーがサポートしていれば）
    """

    def __init__(
        self,
        provider: LLMProvider,
        name: str = "llm_node",
        description: str = "Generate responses using LLM"
    ):
        super().__init__(name=name, description=description)
        self.provider = provider

    async def execute(self, state: NodeState) -> NodeState:
        """LLM生成を実行"""
        set_node_id(self.name)
        start_time = time.time()
        
        try:
            # プロンプトを取得
            prompt = self._get_prompt(state)
            
            if not prompt:
                raise NodeInputValidationError(
                    "Invalid prompt: must be a non-empty string",
                    details={"node": self.name}
                )

            # パラメータを取得
            temperature = state.data.get("temperature", 0.7)
            max_tokens = state.data.get("max_tokens")
            system_prompt = state.data.get("system_prompt")

            logger.info(f"Generating with {self.provider.__class__.__name__}")
            provider_start_time = time.time()
            
            # プロバイダーを通じて生成
            response_text = await self.provider.generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt
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

        except Exception as e:
            self._handle_error(e, start_time)
            raise
        finally:
            clear_node_id()

    def _get_prompt(self, state: NodeState) -> str:
        """プロンプトを取得"""
        if state.messages:
            # 最後のメッセージが文字列であることを確認
            last_msg = state.messages[-1]
            if isinstance(last_msg, str):
                return last_msg
        return state.data.get("prompt", "")

    def _handle_error(self, error: Exception, start_time: float):
        """エラーハンドリングとロギング"""
        duration = time.time() - start_time
        structured_logger.node_execute(
            self.name,
            self.__class__.__name__,
            duration,
            success=False
        )
        
        if isinstance(error, (NodeInputValidationError, NodeExecutionError)):
            return

        # 未知のエラーをラップ
        if isinstance(error, LLMProviderError):
            raise NodeExecutionError(
                f"LLM provider error in node {self.name}",
                details={
                    "node": self.name,
                    "provider": type(self.provider).__name__,
                },
                original_error=error
            )
        else:
            raise NodeExecutionError(
                f"Unexpected error in LLM node {self.name}",
                details={"node": self.name, "error_type": type(error).__name__},
                original_error=error
            )


class LLMInput(NodeInput):
    """Input model for LLM node"""
    prompt: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None


class LLMOutput(NodeOutput):
    """Output model for LLM node"""
    pass


# ============================================================================
# Handler Function for FastAPI
# ============================================================================

async def llm_node_handler(
    input_data: LLMInput,
    provider: Optional[LLMProvider] = None
) -> LLMOutput:
    """LLMノードのハンドラー関数
    
    FastAPIルートから呼び出されるハンドラー関数。
    依存性注入により、プロバイダーを外部から注入できます。
    
    Args:
        input_data: LLM入力データ
        provider: LLMプロバイダー（省略時はデフォルトのGeminiプロバイダー）
    
    Returns:
        LLMOutput: 実行結果
    
    Example:
        >>> from src.api.dependencies import get_llm_provider
        >>> provider = get_llm_provider()
        >>> result = await llm_node_handler(
        >>>     LLMInput(prompt="Hello"),
        >>>     provider=provider
        >>> )
    """
    # デフォルトプロバイダー
    if provider is None:
        from src.providers.llm.gemini import GeminiProvider
        provider = GeminiProvider(
            api_key=settings.gemini_api_key,
            model="gemini-2.0-flash-exp"
        )
    
    # ノードを作成
    node = LLMNode(provider=provider, name="llm_handler")
    
    # 状態を作成
    state = NodeState()
    state.data["prompt"] = input_data.prompt
    state.data["temperature"] = input_data.temperature
    if input_data.max_tokens:
        state.data["max_tokens"] = input_data.max_tokens
    if input_data.system_prompt:
        state.data["system_prompt"] = input_data.system_prompt
    
    # 実行
    result_state = await node.execute(state)
    
    # 結果を返す
    response = result_state.data.get("llm_response", "")
    return LLMOutput(
        success=True,
        data={"response": response}
    )
