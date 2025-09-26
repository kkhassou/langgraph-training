from typing import Dict, Any
from langgraph.graph import StateGraph, END
from pydantic import BaseModel

from app.nodes.base_node import NodeState
from app.nodes.llm_gemini import GeminiNode


class SimpleChatInput(BaseModel):
    """Input model for simple chat graph"""
    message: str
    temperature: float = 0.7


class SimpleChatOutput(BaseModel):
    """Output model for simple chat graph"""
    response: str
    success: bool = True
    error_message: str = None


class SimpleChatGraph:
    """Simple chat workflow using LangGraph"""

    def __init__(self):
        self.gemini_node = GeminiNode()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(NodeState)

        # Add nodes
        workflow.add_node("gemini", self._gemini_step)

        # Set entry point
        workflow.set_entry_point("gemini")

        # Add edges
        workflow.add_edge("gemini", END)

        return workflow.compile()

    async def _gemini_step(self, state: NodeState) -> NodeState:
        """Execute Gemini LLM step"""
        return await self.gemini_node.execute(state)

    async def run(self, input_data: SimpleChatInput) -> SimpleChatOutput:
        """Run the simple chat workflow"""
        try:
            # Initialize state
            initial_state = NodeState()
            initial_state.messages = [input_data.message]
            initial_state.data = {
                "temperature": input_data.temperature,
                "prompt": input_data.message
            }

            # Run the graph
            result = await self.graph.ainvoke(initial_state)

            # Extract response
            if "error" in result["data"]:
                return SimpleChatOutput(
                    response="",
                    success=False,
                    error_message=result["data"]["error"]
                )

            response = result["data"].get("llm_response", "No response generated")

            return SimpleChatOutput(
                response=response,
                success=True
            )

        except Exception as e:
            return SimpleChatOutput(
                response="",
                success=False,
                error_message=str(e)
            )

    def get_mermaid_diagram(self) -> str:
        """Get Mermaid diagram representation of the graph"""
        return """
graph TD
    A[Start: User Message] --> B[Gemini LLM Node]
    B --> C[End: LLM Response]

    classDef startEnd fill:#e1f5fe
    classDef llm fill:#f3e5f5
    class A,C startEnd
    class B llm
        """