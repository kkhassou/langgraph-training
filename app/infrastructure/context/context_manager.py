from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import tiktoken
from app.infrastructure.vector_stores.base import Document
from app.core.config import settings


@dataclass
class ContextWindow:
    """Represents a context window for RAG"""
    documents: List[Document] = field(default_factory=list)
    query: str = ""
    conversation_history: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    total_tokens: int = 0
    max_tokens: int = 4000  # Conservative limit for context window


@dataclass
class ConversationTurn:
    """Represents a single conversation turn"""
    user_query: str
    ai_response: str
    retrieved_documents: List[Document]
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextManager:
    """Manages context windows and conversation history for RAG"""

    def __init__(self, max_context_tokens: int = 4000):
        self.max_context_tokens = max_context_tokens
        self.conversation_history: List[ConversationTurn] = []
        self.encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        try:
            return len(self.encoding.encode(text))
        except Exception:
            # Fallback to character-based estimation
            return len(text) // 4

    def create_context_window(self,
                            query: str,
                            retrieved_documents: List[Document],
                            include_conversation: bool = True,
                            max_history_turns: int = 3) -> ContextWindow:
        """Create an optimized context window"""

        window = ContextWindow(
            query=query,
            max_tokens=self.max_context_tokens
        )

        # Add conversation history if requested
        if include_conversation and self.conversation_history:
            recent_history = self.conversation_history[-max_history_turns:]
            for turn in recent_history:
                window.conversation_history.append(f"User: {turn.user_query}")
                window.conversation_history.append(f"Assistant: {turn.ai_response}")

        # Calculate tokens used by query and conversation
        query_tokens = self.count_tokens(query)
        history_tokens = sum(self.count_tokens(msg) for msg in window.conversation_history)

        # Reserve tokens for response and system prompt
        response_reserve = 1000
        system_prompt_reserve = 500
        available_tokens = self.max_context_tokens - query_tokens - history_tokens - response_reserve - system_prompt_reserve

        # Add documents until we reach token limit
        current_tokens = 0
        for doc in retrieved_documents:
            doc_tokens = self.count_tokens(doc.content)

            if current_tokens + doc_tokens <= available_tokens:
                window.documents.append(doc)
                current_tokens += doc_tokens
            else:
                # Try to fit a truncated version
                remaining_tokens = available_tokens - current_tokens
                if remaining_tokens > 100:  # Minimum meaningful size
                    truncated_content = self._truncate_to_tokens(doc.content, remaining_tokens)
                    truncated_doc = Document(
                        id=doc.id + "_truncated",
                        content=truncated_content,
                        metadata={**doc.metadata, "truncated": True}
                    )
                    window.documents.append(truncated_doc)
                break

        window.total_tokens = query_tokens + history_tokens + current_tokens
        window.metadata = {
            "query_tokens": query_tokens,
            "history_tokens": history_tokens,
            "documents_tokens": current_tokens,
            "documents_count": len(window.documents),
            "truncated_documents": len([d for d in window.documents if d.metadata.get("truncated", False)])
        }

        return window

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit"""
        if self.count_tokens(text) <= max_tokens:
            return text

        # Binary search for optimal truncation point
        left, right = 0, len(text)
        result = text

        while left < right:
            mid = (left + right + 1) // 2
            candidate = text[:mid]

            if self.count_tokens(candidate) <= max_tokens:
                result = candidate
                left = mid
            else:
                right = mid - 1

        # Try to end at a sentence boundary
        sentences = result.split('。')
        if len(sentences) > 1:
            result = '。'.join(sentences[:-1]) + '。'

        return result

    def add_conversation_turn(self,
                            user_query: str,
                            ai_response: str,
                            retrieved_documents: List[Document],
                            metadata: Dict[str, Any] = None):
        """Add a conversation turn to history"""
        turn = ConversationTurn(
            user_query=user_query,
            ai_response=ai_response,
            retrieved_documents=retrieved_documents,
            metadata=metadata or {}
        )
        self.conversation_history.append(turn)

        # Keep only recent history to manage memory
        max_history = 10
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]

    def generate_contextualized_prompt(self, window: ContextWindow) -> str:
        """Generate a contextualized prompt for RAG"""

        # System prompt
        system_prompt = """あなたは高精度な質問応答システムです。提供された文脈情報を参考にして、ユーザーの質問に正確に答えてください。

重要な指示:
1. 文脈情報に基づいて正確に答える
2. 文脈情報にない内容については推測せず、「提供された情報では分かりません」と答える
3. 複数の文書から情報を統合して包括的な回答を作成する
4. 情報源が複数ある場合は、それを明記する
5. 自然で読みやすい日本語で回答する"""

        # Conversation history
        history_section = ""
        if window.conversation_history:
            history_section = "\n\n会話履歴:\n" + "\n".join(window.conversation_history)

        # Retrieved documents
        context_section = "\n\n文脈情報:\n"
        for i, doc in enumerate(window.documents, 1):
            context_section += f"\n[文書 {i}]"
            if doc.metadata.get("title"):
                context_section += f" タイトル: {doc.metadata['title']}"
            if doc.metadata.get("source"):
                context_section += f" 出典: {doc.metadata['source']}"
            context_section += f"\n内容: {doc.content}\n"

        # Current query
        query_section = f"\n\n質問: {window.query}"

        # Response instruction
        response_section = "\n\n回答:"

        full_prompt = system_prompt + history_section + context_section + query_section + response_section

        return full_prompt

    def get_context_stats(self) -> Dict[str, Any]:
        """Get context manager statistics"""
        return {
            "conversation_turns": len(self.conversation_history),
            "max_context_tokens": self.max_context_tokens,
            "total_queries": len(self.conversation_history),
            "average_response_length": sum(
                self.count_tokens(turn.ai_response)
                for turn in self.conversation_history
            ) / len(self.conversation_history) if self.conversation_history else 0
        }

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()

    def export_conversation(self) -> str:
        """Export conversation history as JSON"""
        export_data = []
        for turn in self.conversation_history:
            export_data.append({
                "user_query": turn.user_query,
                "ai_response": turn.ai_response,
                "timestamp": turn.timestamp.isoformat(),
                "retrieved_documents_count": len(turn.retrieved_documents),
                "metadata": turn.metadata
            })
        return json.dumps(export_data, ensure_ascii=False, indent=2)