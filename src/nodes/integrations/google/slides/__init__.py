"""Google Slides Integration Module

Google Slidesとの統合機能を提供します。
"""

from .node import (
    SlidesNode,
    SlidesInput,
    slides_node,
    slides_node_handler
)

__all__ = [
    "SlidesNode",
    "SlidesInput",
    "slides_node",
    "slides_node_handler"
]
