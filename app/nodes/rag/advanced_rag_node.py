from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.nodes.base_node import BaseNode, NodeState, NodeInput, NodeOutput
from app.infrastructure.embeddings.gemini import GeminiEmbeddingProvider
from app.infrastructure.vector_stores.supabase import SupabaseVectorStore, Document
from app.infrastructure.search.hybrid_search import HybridSearchProvider
from app.infrastructure.search.base import SearchQuery
from app.infrastructure.context.context_manager import ContextManager
from app.nodes.llm_gemini import GeminiNode
from app.core.config import settings


class AdvancedRAGInput(NodeInput):
    """Input model for advanced RAG node"""
    query: str
    collection_name: str = "default_collection"
    search_type: str = "hybrid"
    top_k: int = 5
    include_conversation: bool = True
    max_history_turns: int = 3
    semantic_weight: float = 0.7
    bm25_weight: float = 0.3
    context_optimization: bool = True


class AdvancedRAGOutput(NodeOutput):
    """Output model for advanced RAG node"""
    answer: str
    retrieved_documents: List[Dict[str, Any]]
    context_stats: Dict[str, Any]
    search_metadata: Dict[str, Any]


class AdvancedRAGNode(BaseNode):
    """Advanced RAG node with context management and optimized retrieval"""

    def __init__(self):
        super().__init__(
            name="advanced_rag_node",
            description="Advanced RAG with context management and conversation history"
        )
        self.embedding_provider = None
        self.vector_store = None
        self.search_provider = None
        self.llm_node = None
        self.context_manager = ContextManager()

    def _initialize_components(self):
        """Initialize RAG components lazily"""
        if self.embedding_provider is None:
            self.embedding_provider = GeminiEmbeddingProvider(
                model_name=settings.gemini_embedding_model,
                dimension=settings.embedding_dimension
            )

        if self.vector_store is None:
            self.vector_store = SupabaseVectorStore(
                dimension=settings.embedding_dimension
            )

        if self.search_provider is None:
            self.search_provider = HybridSearchProvider()

        if self.llm_node is None:
            self.llm_node = GeminiNode()

    async def execute(self, state: NodeState) -> NodeState:
        """Execute advanced RAG workflow"""
        try:
            self._initialize_components()

            # Extract parameters
            query = state.data.get("query", "")
            collection_name = state.data.get("collection_name", "default_collection")
            search_type = state.data.get("search_type", "hybrid")
            top_k = state.data.get("top_k", 5)
            include_conversation = state.data.get("include_conversation", True)
            max_history_turns = state.data.get("max_history_turns", 3)
            semantic_weight = state.data.get("semantic_weight", 0.7)
            bm25_weight = state.data.get("bm25_weight", 0.3)
            context_optimization = state.data.get("context_optimization", True)

            if not query:
                state.data["error"] = "Query is required for RAG"
                return state

            # Step 1: Query enhancement (expand query with conversation context)
            enhanced_query = await self._enhance_query(query, include_conversation)

            # Step 2: Retrieve documents using hybrid search
            search_query = SearchQuery(
                text=enhanced_query,
                top_k=top_k
            )

            # Configure search weights
            self.search_provider.set_weights(semantic_weight, bm25_weight)

            # For demonstration, create sample documents (in real implementation, retrieve from vector store)
            sample_documents = await self._get_sample_documents(collection_name, query)

            # Perform search
            search_results = await self.search_provider.search(search_query, sample_documents)
            retrieved_documents = [result.document for result in search_results]

            # Step 3: Context optimization
            if context_optimization:
                context_window = self.context_manager.create_context_window(
                    query=query,
                    retrieved_documents=retrieved_documents,
                    include_conversation=include_conversation,
                    max_history_turns=max_history_turns
                )
            else:
                # Simple context without optimization
                from app.infrastructure.context.context_manager import ContextWindow
                context_window = ContextWindow(
                    documents=retrieved_documents,
                    query=query
                )

            # Step 4: Generate contextualized prompt
            if context_optimization:
                prompt = self.context_manager.generate_contextualized_prompt(context_window)
            else:
                prompt = self._create_simple_prompt(query, retrieved_documents)

            # Step 5: Generate response
            llm_state = NodeState()
            llm_state.messages = [prompt]
            llm_result = await self.llm_node.execute(llm_state)
            ai_response = llm_result.data.get("llm_response", "No response generated")

            # Step 6: Update conversation history
            self.context_manager.add_conversation_turn(
                user_query=query,
                ai_response=ai_response,
                retrieved_documents=retrieved_documents,
                metadata={
                    "search_type": search_type,
                    "semantic_weight": semantic_weight,
                    "bm25_weight": bm25_weight
                }
            )

            # Prepare output data
            retrieved_docs_data = []
            for i, doc in enumerate(retrieved_documents):
                doc_data = {
                    "id": doc.id,
                    "content": doc.content[:500] + "..." if len(doc.content) > 500 else doc.content,
                    "metadata": doc.metadata,
                    "rank": i
                }
                retrieved_docs_data.append(doc_data)

            # Context and search statistics
            context_stats = self.context_manager.get_context_stats()
            context_stats.update({
                "current_window_tokens": context_window.total_tokens,
                "documents_used": len(context_window.documents),
                "conversation_included": include_conversation
            })

            search_metadata = {
                "search_type": search_type,
                "enhanced_query": enhanced_query,
                "semantic_weight": semantic_weight,
                "bm25_weight": bm25_weight,
                "total_retrieved": len(retrieved_documents)
            }

            # Update state
            state.data.update({
                "rag_answer": ai_response,
                "retrieved_documents": retrieved_docs_data,
                "context_stats": context_stats,
                "search_metadata": search_metadata,
                "context_window": {
                    "total_tokens": context_window.total_tokens,
                    "metadata": context_window.metadata
                }
            })

            state.metadata["node"] = self.name
            state.metadata["rag_advanced"] = True

            return state

        except Exception as e:
            state.data["error"] = f"Advanced RAG execution failed: {str(e)}"
            state.metadata["error_node"] = self.name
            return state

    async def _enhance_query(self, query: str, include_conversation: bool) -> str:
        """Enhance query with conversation context"""
        if not include_conversation or not self.context_manager.conversation_history:
            return query

        # Get recent conversation context
        recent_turns = self.context_manager.conversation_history[-2:]
        if not recent_turns:
            return query

        # Simple query enhancement (can be made more sophisticated)
        context_terms = []
        for turn in recent_turns:
            # Extract key terms from recent queries
            words = turn.user_query.split()
            context_terms.extend([w for w in words if len(w) > 3])

        # Add relevant context terms to current query
        if context_terms:
            unique_terms = list(set(context_terms))[:3]  # Top 3 context terms
            enhanced_query = f"{query} {' '.join(unique_terms)}"
            return enhanced_query

        return query

    async def _get_sample_documents(self, collection_name: str, query: str) -> List[Document]:
        """Get sample documents for demonstration (replace with real vector store retrieval)"""
        # This is a placeholder implementation
        # In a real implementation, you would retrieve documents from the vector store
        sample_docs = [
            Document(
                id="doc_1",
                content="機械学習は人工知能の一分野で、コンピュータがデータから学習する技術です。教師あり学習、教師なし学習、強化学習の3つの主要なタイプがあります。",
                metadata={"title": "機械学習の基礎", "source": "AI教科書", "category": "technology"}
            ),
            Document(
                id="doc_2",
                content="Pythonは機械学習で最も人気のあるプログラミング言語です。scikit-learn、TensorFlow、PyTorchなどの豊富なライブラリが利用できます。",
                metadata={"title": "Python機械学習", "source": "プログラミングガイド", "category": "programming"}
            ),
            Document(
                id="doc_3",
                content="深層学習は機械学習のサブセットで、人工ニューラルネットワークを使用して複雑なパターンを学習します。画像認識、自然言語処理、音声認識などに応用されています。",
                metadata={"title": "深層学習入門", "source": "AI研究論文", "category": "deep_learning"}
            )
        ]

        # Generate embeddings for sample documents
        for doc in sample_docs:
            if doc.embedding is None:
                doc.embedding = await self.embedding_provider.embed_text(doc.content)

        return sample_docs

    def _create_simple_prompt(self, query: str, documents: List[Document]) -> str:
        """Create a simple prompt without context optimization"""
        context_parts = []
        for i, doc in enumerate(documents, 1):
            context_parts.append(f"文書{i}: {doc.content}")

        context = "\n\n".join(context_parts)

        prompt = f"""以下の文脈情報を参考にして、質問に答えてください。

文脈情報:
{context}

質問: {query}

回答:"""
        return prompt

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        history = []
        for turn in self.context_manager.conversation_history:
            history.append({
                "user_query": turn.user_query,
                "ai_response": turn.ai_response,
                "timestamp": turn.timestamp.isoformat(),
                "retrieved_documents_count": len(turn.retrieved_documents)
            })
        return history

    def clear_conversation(self):
        """Clear conversation history"""
        self.context_manager.clear_history()


async def advanced_rag_handler(input_data: AdvancedRAGInput) -> AdvancedRAGOutput:
    """Standalone handler for advanced RAG node"""
    try:
        node = AdvancedRAGNode()
        state = NodeState()
        state.data = {
            "query": input_data.query,
            "collection_name": input_data.collection_name,
            "search_type": input_data.search_type,
            "top_k": input_data.top_k,
            "include_conversation": input_data.include_conversation,
            "max_history_turns": input_data.max_history_turns,
            "semantic_weight": input_data.semantic_weight,
            "bm25_weight": input_data.bm25_weight,
            "context_optimization": input_data.context_optimization
        }

        result_state = await node.execute(state)

        if "error" in result_state.data:
            return AdvancedRAGOutput(
                answer="",
                retrieved_documents=[],
                context_stats={},
                search_metadata={},
                success=False,
                error_message=result_state.data["error"]
            )

        return AdvancedRAGOutput(
            answer=result_state.data.get("rag_answer", ""),
            retrieved_documents=result_state.data.get("retrieved_documents", []),
            context_stats=result_state.data.get("context_stats", {}),
            search_metadata=result_state.data.get("search_metadata", {}),
            data=result_state.data
        )

    except Exception as e:
        return AdvancedRAGOutput(
            answer="",
            retrieved_documents=[],
            context_stats={},
            search_metadata={},
            success=False,
            error_message=str(e)
        )