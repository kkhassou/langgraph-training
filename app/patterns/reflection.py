from typing import Dict, Any
from langgraph.graph import StateGraph, END
from pydantic import BaseModel

from app.nodes.base_node import NodeState
from app.nodes.llm_gemini import GeminiNode


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
Please complete the following task with high quality:

{task}

Provide a comprehensive and well-structured response.
            """.strip()
        else:
            # Use feedback for improvement
            previous_output = state.data.get("current_output", "")
            feedback = state.data.get("feedback", "")

            prompt = f"""
Original task: {task}

Previous attempt:
{previous_output}

Feedback for improvement:
{feedback}

Please provide an improved version that addresses the feedback while maintaining the original task requirements.
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
Please critically analyze the following response to the given task:

Task: {task}

Response to evaluate:
{current_output}

Provide detailed feedback on:
1. Completeness - Does it fully address the task?
2. Quality - Is it well-structured and clear?
3. Accuracy - Is the information correct?
4. Areas for improvement - What specific improvements could be made?

Rate the overall quality from 1-10 and provide specific suggestions for improvement.
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
            if "error" in result.data:
                return ReflectionOutput(
                    final_output="",
                    success=False,
                    error_message=result.data["error"]
                )

            final_output = result.data.get("current_output", "No output generated")
            iterations = result.data.get("iteration", 0)
            improvement_history = result.data.get("improvement_history", [])

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