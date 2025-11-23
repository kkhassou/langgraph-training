"""Provider Interfaces - 抽象インターフェース

このモジュールは、LLM、RAG、Documentなどの
プロバイダーの抽象インターフェースを定義します。

具象実装は src/providers/ に配置されます。
"""

from .llm import LLMProvider
from .rag import RAGProvider, RAGResult
from .document import DocumentProvider, SlideContent

__all__ = [
    "LLMProvider",
    "RAGProvider",
    "RAGResult",
    "DocumentProvider",
    "SlideContent",
]



