"""Gemini LLM Node - LangGraph node for Gemini LLM interactions"""

from typing import Dict, Any
import logging

from src.nodes.base import BaseNode, NodeState, NodeInput, NodeOutput
from src.services.llm.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class GeminiNode(BaseNode):
    """Node for interacting with Google Gemini LLM"""

    def __init__(self):
        super().__init__(
            name="gemini_llm",
            description="Generate responses using Google Gemini LLM"
        )

    async def execute(self, state: NodeState) -> NodeState:
        """Execute Gemini LLM generation"""
        try:
            # Get the latest message or use default prompt
            if state.messages:
                prompt = state.messages[-1]
            else:
                prompt = state.data.get("prompt", "Hello, how can I help you?")

            # Get parameters
            temperature = state.data.get("temperature", 0.7)
            max_tokens = state.data.get("max_tokens")

            # ✅ GeminiServiceを使ってシンプルに呼び出し
            logger.info(f"Generating response with Gemini (temperature: {temperature})")
            response_text = await GeminiService.generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Update state
            state.messages.append(response_text)
            state.data["llm_response"] = response_text
            state.metadata["node"] = self.name

            return state

        except Exception as e:
            logger.error(f"Error in Gemini node: {e}")
            state.data["error"] = str(e)
            state.metadata["error_node"] = self.name
            return state


class GeminiInput(NodeInput):
    """Input model for Gemini node"""
    prompt: str
    temperature: float = 0.7
    max_tokens: int = 1000


class GeminiOutput(NodeOutput):
    """Output model for Gemini node"""
    pass


async def gemini_node_handler(input_data: GeminiInput) -> GeminiOutput:
    """Standalone handler for Gemini node API endpoint"""
    try:
        node = GeminiNode()
        state = NodeState()
        state.messages = [input_data.prompt]
        state.data["temperature"] = input_data.temperature
        state.data["max_tokens"] = input_data.max_tokens

        result_state = await node.execute(state)

        if "error" in result_state.data:
            return GeminiOutput(
                output_text="",
                success=False,
                error_message=result_state.data["error"]
            )

        return GeminiOutput(
            output_text=result_state.data.get("llm_response", ""),
            data=result_state.data
        )

    except Exception as e:
        return GeminiOutput(
            output_text="",
            success=False,
            error_message=str(e)
        )
