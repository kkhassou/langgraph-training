"""Google Vertex Ai Integration Node

Google Vertex Aiとの統合を行うノード実装。
MCP (Model Context Protocol) サーバーを介してGoogle APIと通信します。
"""



from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import logging

from src.mcp.google.vertex_ai.client import VertexAIMCPService
from src.nodes.base import BaseNode, NodeResult

logger = logging.getLogger(__name__)


class VertexAIInput(BaseModel):
    """Input schema for Vertex AI MCP node"""
    action: str = Field(..., description="Action to perform: generate_text, chat, generate_embeddings, list_models")

    # For generate_text
    prompt: Optional[str] = Field(None, description="Text prompt for generation")
    model: Optional[str] = Field("gemini-1.5-flash", description="Model name")
    temperature: Optional[float] = Field(0.7, description="Temperature (0.0-2.0)")
    max_tokens: Optional[int] = Field(1024, description="Maximum output tokens")

    # For chat
    message: Optional[str] = Field(None, description="User message for chat")
    history: Optional[List[Dict[str, str]]] = Field(None, description="Conversation history")

    # For generate_embeddings
    texts: Optional[List[str]] = Field(None, description="List of texts to embed")


class VertexAINode(BaseNode):
    """Node for Vertex AI operations via MCP (Model Context Protocol) server"""

    def __init__(self):
        super().__init__("vertex-ai-mcp")
        self.vertex_ai_service = VertexAIMCPService()

    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """Execute Vertex AI MCP node"""
        try:
            action = input_data.get("action")

            if action == "generate_text":
                prompt = input_data.get("prompt")
                if not prompt:
                    raise ValueError("prompt is required for generate_text action")

                model = input_data.get("model", "gemini-1.5-flash")
                temperature = input_data.get("temperature", 0.7)
                max_tokens = input_data.get("max_tokens", 1024)

                result = await self.vertex_ai_service.generate_text(
                    prompt, model, temperature, max_tokens
                )
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "generate_text", "model": model}
                )

            elif action == "chat":
                message = input_data.get("message")
                if not message:
                    raise ValueError("message is required for chat action")

                model = input_data.get("model", "gemini-1.5-flash")
                history = input_data.get("history")

                result = await self.vertex_ai_service.chat(message, model, history)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "chat", "model": model}
                )

            elif action == "generate_embeddings":
                texts = input_data.get("texts")
                if not texts:
                    raise ValueError("texts is required for generate_embeddings action")

                model = input_data.get("model", "text-embedding-004")

                result = await self.vertex_ai_service.generate_embeddings(texts, model)
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "generate_embeddings", "model": model}
                )

            elif action == "list_models":
                result = await self.vertex_ai_service.list_models()
                return NodeResult(
                    success=True,
                    data=result,
                    metadata={"action": "list_models"}
                )

            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Error in Vertex AI MCP node: {e}")
            return NodeResult(
                success=False,
                error=str(e),
                metadata={"action": input_data.get("action")}
            )

    async def cleanup(self):
        """Cleanup Vertex AI MCP resources"""
        try:
            await self.vertex_ai_service.disconnect()
        except Exception as e:
            logger.error(f"Error during Vertex AI MCP cleanup: {e}")


# Create node instance
vertex_ai_node = VertexAINode()


async def vertex_ai_node_handler(input_data: VertexAIInput) -> Dict[str, Any]:
    """Handler function for Vertex AI MCP node endpoint"""
    result = await vertex_ai_node.execute(input_data.model_dump())
    return result.model_dump()
