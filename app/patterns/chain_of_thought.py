from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from pydantic import BaseModel

from app.nodes.base_node import NodeState
from app.nodes.llm_gemini import GeminiNode


class ChainOfThoughtInput(BaseModel):
    """Input model for Chain of Thought pattern"""
    problem: str
    reasoning_steps: int = 3


class ChainOfThoughtOutput(BaseModel):
    """Output model for Chain of Thought pattern"""
    final_answer: str
    reasoning_steps: List[Dict[str, str]] = []
    thought_process: str = ""
    success: bool = True
    error_message: str = None


class ChainOfThoughtGraph:
    """Chain of Thought pattern implementation using LangGraph"""

    def __init__(self):
        self.llm_node = GeminiNode()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow for Chain of Thought pattern"""
        workflow = StateGraph(NodeState)

        # Add nodes
        workflow.add_node("break_down", self._break_down_step)
        workflow.add_node("reason_step", self._reasoning_step)
        workflow.add_node("synthesize", self._synthesize_step)

        # Set entry point
        workflow.set_entry_point("break_down")

        # Add conditional edges
        workflow.add_edge("break_down", "reason_step")

        workflow.add_conditional_edges(
            "reason_step",
            self._should_continue_reasoning,
            {
                "continue": "reason_step",
                "synthesize": "synthesize"
            }
        )

        workflow.add_edge("synthesize", END)

        return workflow.compile()

    async def _break_down_step(self, state: NodeState) -> NodeState:
        """Break down the problem into reasoning steps"""
        problem = state.data.get("problem", "")
        max_steps = state.data.get("reasoning_steps", 3)

        prompt = f"""
Please break down the following problem into {max_steps} clear reasoning steps:

Problem: {problem}

Provide exactly {max_steps} steps in this format:
Step 1: [Clear description of what to analyze or determine]
Step 2: [Next logical step in the reasoning process]
Step 3: [Final step leading to the answer]

Just list the steps, don't solve them yet.
        """.strip()

        state.messages = [prompt]
        state.data["prompt"] = prompt

        result = await self.llm_node.execute(state)

        if "llm_response" in result.data:
            # Parse the steps
            steps_text = result.data["llm_response"]
            steps = self._parse_reasoning_steps(steps_text)
            result.data["reasoning_steps"] = steps
            result.data["current_step"] = 0
            result.data["completed_steps"] = []

        return result

    async def _reasoning_step(self, state: NodeState) -> NodeState:
        """Execute one reasoning step"""
        if "error" in state.data:
            return state

        current_step = state.data.get("current_step", 0)
        reasoning_steps = state.data.get("reasoning_steps", [])
        completed_steps = state.data.get("completed_steps", [])

        if current_step >= len(reasoning_steps):
            return state

        # Get current step to work on
        step_description = reasoning_steps[current_step]
        problem = state.data.get("problem", "")

        # Build context from previous steps
        context = ""
        if completed_steps:
            context = "\nPrevious reasoning:\n"
            for i, completed in enumerate(completed_steps, 1):
                context += f"Step {i}: {completed['reasoning']}\n"

        prompt = f"""
Problem: {problem}

{context}

Current Step {current_step + 1}: {step_description}

Think through this step carefully and provide your reasoning. Be specific and detailed in your analysis.
        """.strip()

        state.messages = [prompt]
        state.data["prompt"] = prompt

        result = await self.llm_node.execute(state)

        if "llm_response" in result.data:
            # Store the completed step
            completed_step = {
                "step": str(current_step + 1),
                "description": step_description,
                "reasoning": result.data["llm_response"]
            }

            result.data["completed_steps"].append(completed_step)
            result.data["current_step"] = current_step + 1

        return result

    async def _synthesize_step(self, state: NodeState) -> NodeState:
        """Synthesize all reasoning steps into final answer"""
        if "error" in state.data:
            return state

        problem = state.data.get("problem", "")
        completed_steps = state.data.get("completed_steps", [])

        # Build the complete reasoning chain
        reasoning_chain = ""
        for step in completed_steps:
            reasoning_chain += f"Step {step['step']}: {step['description']}\n"
            reasoning_chain += f"Reasoning: {step['reasoning']}\n\n"

        prompt = f"""
Problem: {problem}

Complete reasoning process:
{reasoning_chain}

Based on the step-by-step reasoning above, provide the final answer to the problem.
Summarize the key insights from each step and draw your conclusion.
        """.strip()

        state.messages = [prompt]
        state.data["prompt"] = prompt

        result = await self.llm_node.execute(state)

        if "llm_response" in result.data:
            result.data["final_answer"] = result.data["llm_response"]
            result.data["thought_process"] = reasoning_chain

        return result

    def _parse_reasoning_steps(self, steps_text: str) -> List[str]:
        """Parse reasoning steps from LLM response"""
        steps = []
        lines = steps_text.strip().split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith("Step") and ":" in line:
                # Extract the step description after the colon
                step_desc = line.split(":", 1)[1].strip()
                steps.append(step_desc)

        return steps

    def _should_continue_reasoning(self, state: NodeState) -> str:
        """Decide whether to continue with more reasoning steps"""
        if "error" in state.data:
            return "synthesize"

        current_step = state.data.get("current_step", 0)
        reasoning_steps = state.data.get("reasoning_steps", [])

        if current_step < len(reasoning_steps):
            return "continue"
        else:
            return "synthesize"

    async def run(self, input_data: ChainOfThoughtInput) -> ChainOfThoughtOutput:
        """Run the Chain of Thought workflow"""
        try:
            # Initialize state
            initial_state = NodeState()
            initial_state.data = {
                "problem": input_data.problem,
                "reasoning_steps": input_data.reasoning_steps
            }

            # Run the graph
            result = await self.graph.ainvoke(initial_state)

            # Extract results
            if "error" in result["data"]:
                return ChainOfThoughtOutput(
                    final_answer="",
                    success=False,
                    error_message=result["data"]["error"]
                )

            final_answer = result["data"].get("final_answer", "No answer generated")
            reasoning_steps = result["data"].get("completed_steps", [])
            thought_process = result["data"].get("thought_process", "")

            return ChainOfThoughtOutput(
                final_answer=final_answer,
                reasoning_steps=reasoning_steps,
                thought_process=thought_process,
                success=True
            )

        except Exception as e:
            return ChainOfThoughtOutput(
                final_answer="",
                success=False,
                error_message=str(e)
            )

    def get_mermaid_diagram(self) -> str:
        """Get Mermaid diagram representation of the graph"""
        return """
graph TD
    A[Start: Problem Input] --> B[Break Down into Steps]
    B --> C[Execute Reasoning Step]
    C --> D{More Steps?}
    D -->|Yes| C
    D -->|No| E[Synthesize Final Answer]
    E --> F[End: Complete Reasoning Chain]

    classDef startEnd fill:#e1f5fe
    classDef breakdown fill:#fff3e0
    classDef reasoning fill:#f3e5f5
    classDef decision fill:#e8f5e8
    classDef synthesis fill:#e8f5e8

    class A,F startEnd
    class B breakdown
    class C reasoning
    class D decision
    class E synthesis
        """