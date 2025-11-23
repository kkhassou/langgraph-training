"""Code Node - Pythonコード実行ノード

小規模なデータ加工や計算を行います。
"""

from typing import Any, Dict, Callable
from src.nodes.base import BaseNode, NodeState


class CodeNode(BaseNode):
    """コード実行ノード
    
    任意のPython関数を実行してデータを加工します。
    
    Example:
        >>> def calculate(state):
        ...     return state.data["a"] + state.data["b"]
        >>> node = CodeNode(func=calculate, output_key="sum")
    """

    def __init__(
        self,
        func: Callable[[NodeState], Any],
        output_key: str = "code_output",
        name: str = "code_node",
        description: str = "Execute Python code"
    ):
        super().__init__(name=name, description=description)
        self.func = func
        self.output_key = output_key

    async def execute(self, state: NodeState) -> NodeState:
        """コードを実行"""
        try:
            result = self.func(state)
            state.data[self.output_key] = result
            state.metadata["node"] = self.name
            return state
        except Exception as e:
            state.data["error"] = str(e)
            state.metadata["error_node"] = self.name
            return state

