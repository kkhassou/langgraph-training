from typing import Dict, Any
from langgraph.graph import StateGraph, END
from pydantic import BaseModel

from src.nodes.base import NodeState
from src.nodes.llm.gemini import GeminiNode


class ReflectionInput(BaseModel):
    """Input model for reflection pattern"""
    task: str
    max_iterations: int = 3
    improvement_threshold: float = 0.1


class ReflectionOutput(BaseModel):
    """Output model for reflection pattern"""
    final_output: str
    iterations: int = 0
    improvement_history: list = []
    success: bool = True
    error_message: str = None


class ReflectionGraph:
    """Reflection pattern implementation using LangGraph"""

    def __init__(self):
        self.generator_node = GeminiNode()
        self.critic_node = GeminiNode()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow for reflection pattern"""
        workflow = StateGraph(NodeState)

        # Add nodes
        workflow.add_node("generate", self._generate_step)
        workflow.add_node("reflect", self._reflect_step)
        workflow.add_node("improve", self._improve_step)

        # Set entry point
        workflow.set_entry_point("generate")

        # Add conditional edges
        workflow.add_conditional_edges(
            "generate",
            self._should_reflect,
            {
                "reflect": "reflect",
                "end": END
            }
        )

        workflow.add_conditional_edges(
            "reflect",
            self._should_improve,
            {
                "improve": "improve",
                "end": END
            }
        )

        workflow.add_conditional_edges(
            "improve",
            self._should_continue,
            {
                "reflect": "reflect",
                "end": END
            }
        )

        return workflow.compile()

    async def _generate_step(self, state: NodeState) -> NodeState:
        """Generate initial response"""
        task = state.data.get("task", "")
        iteration = state.data.get("iteration", 0)

        if iteration == 0:
            prompt = f"""
以下のタスクを高品質で完了してください：

{task}

包括的で構造化された回答を日本語で提供してください。
            """.strip()
        else:
            # Use feedback for improvement
            previous_output = state.data.get("current_output", "")
            feedback = state.data.get("feedback", "")

            prompt = f"""
元のタスク：{task}

前回の回答：
{previous_output}

改善のためのフィードバック：
{feedback}

フィードバックに対応しながら、元のタスク要件を維持した改善版を日本語で提供してください。
            """.strip()

        state.messages = [prompt]
        state.data["prompt"] = prompt

        result = await self.generator_node.execute(state)

        # Store the generated output
        if "llm_response" in result.data:
            result.data["current_output"] = result.data["llm_response"]

        return result

    async def _reflect_step(self, state: NodeState) -> NodeState:
        """Reflect on the generated output and provide feedback"""
        if "error" in state.data:
            return state

        current_output = state.data.get("current_output", "")
        task = state.data.get("task", "")

        prompt = f"""
以下のタスクに対する回答を批判的に分析してください：

タスク：{task}

評価する回答：
{current_output}

以下の点について詳細なフィードバックを日本語で提供してください：
1. 完全性 - タスクに完全に対応しているか？
2. 品質 - 構造化され、明確か？
3. 正確性 - 情報は正確か？
4. 改善点 - どのような具体的な改善ができるか？

全体的な品質を1-10で評価し、具体的な改善提案を提供してください。
        """.strip()

        state.messages = [prompt]
        state.data["prompt"] = prompt

        result = await self.critic_node.execute(state)

        # Store the feedback
        if "llm_response" in result.data:
            result.data["feedback"] = result.data["llm_response"]

        return result

    async def _improve_step(self, state: NodeState) -> NodeState:
        """Update iteration counter and prepare for next iteration"""
        iteration = state.data.get("iteration", 0)
        iteration += 1
        state.data["iteration"] = iteration

        # Store improvement history
        if "improvement_history" not in state.data:
            state.data["improvement_history"] = []

        state.data["improvement_history"].append({
            "iteration": iteration,
            "output": state.data.get("current_output", ""),
            "feedback": state.data.get("feedback", "")
        })

        return state

    def _should_reflect(self, state: NodeState) -> str:
        """Decide whether to reflect on the output"""
        if "error" in state.data:
            return "end"

        iteration = state.data.get("iteration", 0)
        max_iterations = state.data.get("max_iterations", 3)

        if iteration < max_iterations:
            return "reflect"
        else:
            return "end"

    def _should_improve(self, state: NodeState) -> str:
        """Decide whether to improve based on feedback"""
        if "error" in state.data:
            return "end"

        # Simple logic: always try to improve if we have feedback
        feedback = state.data.get("feedback", "")
        if feedback and "10/10" not in feedback.lower():
            return "improve"
        else:
            return "end"

    def _should_continue(self, state: NodeState) -> str:
        """Decide whether to continue with another iteration"""
        if "error" in state.data:
            return "end"

        iteration = state.data.get("iteration", 0)
        max_iterations = state.data.get("max_iterations", 3)

        if iteration < max_iterations:
            return "reflect"
        else:
            return "end"

    async def run(self, input_data: ReflectionInput) -> ReflectionOutput:
        """Run the reflection pattern workflow"""
        try:
            # Initialize state
            initial_state = NodeState()
            initial_state.data = {
                "task": input_data.task,
                "max_iterations": input_data.max_iterations,
                "improvement_threshold": input_data.improvement_threshold,
                "iteration": 0
            }

            # Run the graph
            result = await self.graph.ainvoke(initial_state)

            # Extract results
            if "error" in result["data"]:
                return ReflectionOutput(
                    final_output="",
                    success=False,
                    error_message=result["data"]["error"]
                )

            final_output = result["data"].get("current_output", "No output generated")
            iterations = result["data"].get("iteration", 0)
            improvement_history = result["data"].get("improvement_history", [])

            return ReflectionOutput(
                final_output=final_output,
                iterations=iterations,
                improvement_history=improvement_history,
                success=True
            )

        except Exception as e:
            return ReflectionOutput(
                final_output="",
                success=False,
                error_message=str(e)
            )

    def get_mermaid_diagram(self) -> str:
        """Get Mermaid diagram representation of the graph"""
        return """
graph TD
    A[Start: Task Input] --> B[Generate Initial Response]
    B --> C{Max Iterations Reached?}
    C -->|No| D[Reflect & Analyze]
    C -->|Yes| H[End: Final Output]
    D --> E{Quality Acceptable?}
    E -->|No| F[Improve Response]
    E -->|Yes| H
    F --> G[Update Iteration]
    G --> C

    classDef startEnd fill:#e1f5fe
    classDef generate fill:#f3e5f5
    classDef reflect fill:#fff3e0
    classDef decision fill:#e8f5e8
    classDef improve fill:#e1f5fe

    class A,H startEnd
    class B,F generate
    class D reflect
    class C,E decision
    class G improve
        """