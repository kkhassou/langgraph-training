from typing import Dict, Any
from langgraph.graph import StateGraph, END
from pydantic import BaseModel

from src.nodes.base import NodeState
from src.nodes.llm.gemini import GeminiNode


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
        from langgraph.graph import START

        workflow = StateGraph(NodeState)

        # Add nodes
        workflow.add_node("gemini", self._gemini_step)

        # Set entry point using START constant
        workflow.add_edge(START, "gemini")

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

            # Extract response from final state
            # LangGraph returns the final state, which should be a NodeState
            final_state = result

            # If result is a dictionary (node outputs), get the final node state
            if isinstance(result, dict):
                # Try to get the gemini node result if it exists
                if "gemini" in result:
                    final_state = result["gemini"]
                else:
                    # Otherwise, take the last available state
                    final_state = list(result.values())[-1] if result else initial_state

            if "error" in final_state.data:
                return SimpleChatOutput(
                    response="",
                    success=False,
                    error_message=final_state.data["error"]
                )

            response = final_state.data.get("llm_response", "No response generated")

            return SimpleChatOutput(
                response=response,
                success=True
            )

        except Exception as e:
            import traceback
            error_detail = f"{str(e)} - {traceback.format_exc()}"
            return SimpleChatOutput(
                response="",
                success=False,
                error_message=error_detail
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