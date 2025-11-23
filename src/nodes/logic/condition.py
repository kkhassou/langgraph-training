"""Condition Node - 条件分岐ノード

if-else ロジックをグラフで表現するために使用します。
"""

from typing import Any, Dict, Callable, Optional
from src.nodes.base import BaseNode, NodeState


class ConditionNode(BaseNode):
    """条件分岐ノード
    
    State内のデータを評価し、次のステップを決定します。
    
    Example:
        >>> def check_value(state):
        ...     return "high" if state.data["value"] > 10 else "low"
        >>> node = ConditionNode(condition_fn=check_value)
        >>> state = await node.execute(state)
        >>> print(state.data["condition_result"])  # "high" or "low"
    """

    def __init__(
        self,
        condition_fn: Callable[[NodeState], str],
        name: str = "condition_node",
        description: str = "Evaluate condition and determine next step"
    ):
        super().__init__(name=name, description=description)
        self.condition_fn = condition_fn

    async def execute(self, state: NodeState) -> NodeState:
        """条件評価を実行"""
        try:
            result = self.condition_fn(state)
            state.data["condition_result"] = result
            state.metadata["condition_node"] = self.name
            state.messages.append(f"Condition evaluated: {result}")
            return state
        except Exception as e:
            state.data["error"] = str(e)
            state.metadata["error_node"] = self.name
            return state

