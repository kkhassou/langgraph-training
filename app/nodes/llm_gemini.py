from typing import Dict, Any
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

from app.nodes.base_node import BaseNode, NodeState, NodeInput, NodeOutput
from app.core.config import settings


def validate_gemini_key() -> str:
    """Validate and return Gemini API key"""
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured")
    return settings.gemini_api_key


class GeminiNode(BaseNode):
    """Node for interacting with Google Gemini LLM"""

    def __init__(self):
        super().__init__(
            name="gemini_llm",
            description="Generate responses using Google Gemini LLM"
        )
        self.llm = None

    def _initialize_llm(self):
        """Initialize the Gemini LLM"""
        if self.llm is None:
            api_key = validate_gemini_key()
            genai.configure(api_key=api_key)
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=api_key,
                temperature=0.7
            )

    async def execute(self, state: NodeState) -> NodeState:
        """Execute Gemini LLM generation"""
        try:
            self._initialize_llm()

            # Get the latest message or use default prompt
            if state.messages:
                prompt = state.messages[-1]
            else:
                prompt = state.data.get("prompt", "Hello, how can I help you?")

            # Generate response
            response = await self.llm.ainvoke(prompt)
            response_text = response.content

            # Update state
            state.messages.append(response_text)
            state.data["llm_response"] = response_text
            state.metadata["node"] = self.name

            return state

        except Exception as e:
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