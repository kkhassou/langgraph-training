"""
Chat Atomic Workflow - シンプルなチャット機能

このワークフローは単一のLLMノードを使用して、
ユーザーとの対話を実現します。
"""

from typing import Optional
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
import logging

from src.nodes.base import NodeState
from src.nodes.primitives.llm.gemini.node import LLMNode
from src.core.providers.llm import LLMProvider
from src.providers.llm.gemini import GeminiProvider
from src.core.config import settings

logger = logging.getLogger(__name__)


class ChatInput(BaseModel):
    """Chat workflow input"""
    message: str = Field(..., description="User message")
    temperature: float = Field(default=0.7, description="LLM temperature")
    max_tokens: int = Field(default=1000, description="Maximum tokens to generate")


class ChatOutput(BaseModel):
    """Chat workflow output"""
    response: str = Field(..., description="LLM response")
    success: bool = Field(default=True, description="Success flag")
    error_message: str = Field(default="", description="Error message if any")


class ChatWorkflow:
    """チャットワークフロー（プロバイダー注入可能）
    
    依存性注入パターンを使用し、任意のLLMProviderを注入できます。
    これにより、テスト時のモック化や、異なるLLMサービスへの切り替えが容易になります。
    
    Example:
        >>> # 新しい方法（推奨）
        >>> provider = GeminiProvider(api_key="...", model="...")
        >>> workflow = ChatWorkflow(llm_provider=provider)
        >>> 
        >>> # 既存の方法（後方互換）
        >>> workflow = ChatWorkflow()  # デフォルトプロバイダーを使用
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        """
        Args:
            llm_provider: LLMプロバイダー（省略時はGeminiProvider）
        """
        # ✅ プロバイダーが指定されなければデフォルトを使用
        if llm_provider is None:
            llm_provider = GeminiProvider(
                api_key=settings.gemini_api_key,
                model="gemini-2.0-flash-exp"
            )
        
        self.llm_node = LLMNode(provider=llm_provider, name="chat_llm")
        self.graph = self._build_graph()
        logger.info(f"ChatWorkflow initialized with {llm_provider.__class__.__name__}")

    def _build_graph(self) -> StateGraph:
        """LangGraphを構築"""
        workflow = StateGraph(NodeState)

        # ノードを追加
        workflow.add_node("gemini", self.llm_node.execute)

        # フローを定義
        workflow.add_edge(START, "gemini")
        workflow.add_edge("gemini", END)

        return workflow.compile()

    async def run(self, input_data: ChatInput) -> ChatOutput:
        """ワークフローを実行
        
        Args:
            input_data: チャット入力
            
        Returns:
            ChatOutput: LLMの応答
        """
        try:
            # 状態を作成
            state = NodeState()
            state.messages = [input_data.message]
            state.data["temperature"] = input_data.temperature
            state.data["max_tokens"] = input_data.max_tokens

            # グラフを実行
            logger.info(f"Executing chat workflow with message: {input_data.message[:50]}...")
            result_state = await self.graph.ainvoke(state)

            # エラーチェック
            if "error" in result_state.data:
                return ChatOutput(
                    response="",
                    success=False,
                    error_message=result_state.data["error"]
                )

            # 結果を返す
            response = result_state.data.get("llm_response", "")
            logger.info(f"Chat workflow completed successfully")

            return ChatOutput(
                response=response,
                success=True
            )

        except Exception as e:
            logger.error(f"Error in chat workflow: {e}")
            return ChatOutput(
                response="",
                success=False,
                error_message=str(e)
            )
    
    def get_mermaid_diagram(self) -> str:
        """LangGraphの可視化
        
        Returns:
            Mermaid形式のグラフ定義
        """
        return self.graph.get_graph().draw_mermaid()


