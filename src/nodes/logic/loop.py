"""Loop Node - ループ制御ノード

繰り返し処理の状態管理を行います。
"""

from src.nodes.base import BaseNode, NodeState


class LoopNode(BaseNode):
    """ループ制御ノード
    
    イテレーション回数の管理や、ループ継続条件の判定を行います。
    
    State入力:
        - data["loop_items"]: 処理対象のリスト
        - data["loop_index"]: 現在のインデックス（自動管理）
    
    State出力:
        - data["current_item"]: 現在処理中のアイテム
        - data["loop_continue"]: ループを継続するかどうか
    """

    def __init__(self, name: str = "loop_node", description: str = "Manage loop iteration"):
        super().__init__(name=name, description=description)

    async def execute(self, state: NodeState) -> NodeState:
        """ループ状態を更新"""
        items = state.data.get("loop_items", [])
        index = state.data.get("loop_index", 0)
        
        if index < len(items):
            # 次のアイテムを取得
            state.data["current_item"] = items[index]
            state.data["loop_index"] = index + 1
            state.data["loop_continue"] = True
            state.messages.append(f"Loop iteration {index + 1}/{len(items)}")
        else:
            # ループ終了
            state.data["current_item"] = None
            state.data["loop_continue"] = False
            state.messages.append("Loop finished")
            
            # クリーンアップ（オプション）
            if "loop_index" in state.data:
                del state.data["loop_index"]
        
        state.metadata["node"] = self.name
        return state

