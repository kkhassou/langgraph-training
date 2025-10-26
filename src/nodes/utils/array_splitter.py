"""Array Splitter Node - Generic node to split arrays for parallel processing

This node takes an array and splits it into individual items,
allowing each item to be processed in parallel by subsequent nodes.
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
import logging

from src.nodes.base import BaseNode, NodeResult

logger = logging.getLogger(__name__)


class ArraySplitterInput(BaseModel):
    """Input schema for Array Splitter node"""
    items: List[Any] = Field(..., description="Array of items to split")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata to pass through")


class ArraySplitterNode(BaseNode):
    """Node that splits an array into individual items for parallel processing"""

    def __init__(self):
        super().__init__("array-splitter")

    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """Execute array splitting"""
        try:
            items = input_data.get("items", [])
            metadata = input_data.get("metadata", {})

            if not items:
                logger.warning("No items to split")
                return NodeResult(
                    success=True,
                    data={"split_items": [], "count": 0},
                    metadata={"action": "array_split", "count": 0}
                )

            # Split items with index for tracking
            split_items = []
            for idx, item in enumerate(items):
                split_items.append({
                    "index": idx,
                    "total": len(items),
                    "item": item,
                    "original_metadata": metadata
                })

            logger.info(f"Split {len(items)} items for parallel processing")

            return NodeResult(
                success=True,
                data={
                    "split_items": split_items,
                    "count": len(items)
                },
                metadata={
                    "action": "array_split",
                    "count": len(items)
                }
            )

        except Exception as e:
            logger.error(f"Error in array splitter: {e}")
            return NodeResult(
                success=False,
                error=str(e),
                metadata={"action": "array_split"}
            )


# Create node instance
array_splitter_node = ArraySplitterNode()


async def array_splitter_handler(input_data: ArraySplitterInput) -> Dict[str, Any]:
    """Handler function for Array Splitter node"""
    result = await array_splitter_node.execute(input_data.model_dump())
    return result.model_dump()
