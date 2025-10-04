from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.nodes.base_node import BaseNode, NodeState, NodeInput, NodeOutput
from app.infrastructure.embeddings.gemini import GeminiEmbeddingProvider
from app.infrastructure.vector_stores.supabase import SupabaseVectorStore, Document
from app.infrastructure.vector_stores.local import LocalVectorStore
from app.nodes.llm_gemini import GeminiNode
from app.core.config import settings


class RAGInput(NodeInput):
    """Input model for RAG node"""
    query: str
    collection_name: str = "default_collection"
    top_k: int = 5
    include_metadata: bool = True


class RAGOutput(NodeOutput):
    """Output model for RAG node"""
    answer: str
    retrieved_documents: List[Dict[str, Any]]
    query_embedding: Optional[List[float]] = None
    
    # Ensure output_text is populated for compatibility with NodeOutput
    def __init__(self, **data):
        if 'output_text' not in data and 'answer' in data:
            data['output_text'] = data['answer']
        super().__init__(**data)


class RAGNode(BaseNode):
    """RAG (Retrieval-Augmented Generation) Node"""

    def __init__(self):
        super().__init__(
            name="rag_node",
            description="Retrieve relevant documents and generate augmented response"
        )
        self.embedding_provider = None
        self.vector_store = None
        self.llm_provider = None

    def _initialize_components(self):
        """Initialize RAG components lazily"""
        if self.embedding_provider is None:
            self.embedding_provider = GeminiEmbeddingProvider(
                model_name=settings.gemini_embedding_model,
                dimension=settings.embedding_dimension
            )

        if self.vector_store is None:
            # Try Supabase first, fallback to local store
            try:
                if settings.supabase_url and settings.supabase_key:
                    self.vector_store = SupabaseVectorStore(
                        dimension=settings.embedding_dimension
                    )
                    print("Using Supabase vector store")
                else:
                    raise ValueError("Supabase credentials not configured")
            except Exception as e:
                print(f"Supabase initialization failed: {str(e)}")
                print("Falling back to local vector store")
                self.vector_store = LocalVectorStore(
                    dimension=settings.embedding_dimension
                )
                print("Using local vector store")

        if self.llm_provider is None:
            self.llm_provider = GeminiNode()

    async def execute(self, state: NodeState) -> NodeState:
        """Execute RAG workflow"""
        try:
            self._initialize_components()

            # Get query from state
            query = state.data.get("query", "")
            collection_name = state.data.get("collection_name", "default_collection")
            top_k = state.data.get("top_k", 5)

            if not query:
                state.data["error"] = "Query is required for RAG"
                return state

            # Step 1: Generate query embedding
            query_embedding = await self.embedding_provider.embed_query(query)

            # Step 2: Retrieve relevant documents
            search_results = await self.vector_store.search(
                collection_name=collection_name,
                query_embedding=query_embedding,
                top_k=top_k
            )

            # Step 3: Prepare context from retrieved documents
            context_parts = []
            retrieved_docs = []

            for result in search_results:
                context_parts.append(f"Document {result.rank + 1}: {result.document.content}")
                retrieved_docs.append({
                    "id": result.document.id,
                    "content": result.document.content,
                    "metadata": result.document.metadata,
                    "score": result.score,
                    "rank": result.rank
                })

            context = "\n\n".join(context_parts)

            # Step 4: Generate augmented prompt
            augmented_prompt = self._create_augmented_prompt(query, context)

            # Step 5: Generate response using LLM
            llm_state = NodeState()
            llm_state.messages = [augmented_prompt]
            llm_result = await self.llm_provider.execute(llm_state)
            llm_response = llm_result.data.get("llm_response", "No response generated")

            # Update state with results
            state.data.update({
                "rag_answer": llm_response,
                "retrieved_documents": retrieved_docs,
                "query_embedding": query_embedding,
                "context_used": context
            })

            state.metadata["node"] = self.name
            state.metadata["documents_retrieved"] = len(retrieved_docs)

            return state

        except Exception as e:
            state.data["error"] = f"RAG execution failed: {str(e)}"
            state.metadata["error_node"] = self.name
            return state

    def _create_augmented_prompt(self, query: str, context: str) -> str:
        """Create prompt with retrieved context"""
        return f"""あなたは質問応答システムです。以下の文脈情報を参考にして、ユーザーの質問に答えてください。

文脈情報:
{context}

質問: {query}

回答は以下の点に注意してください：
1. 文脈情報に基づいて正確に答える
2. 文脈情報にない内容については推測しない
3. 情報が不足している場合は明確に述べる
4. 自然で読みやすい日本語で回答する

回答:"""


async def rag_node_handler(input_data: RAGInput) -> RAGOutput:
    """Standalone handler for RAG node API endpoint"""
    try:
        node = RAGNode()
        state = NodeState()
        state.data = {
            "query": input_data.query,
            "collection_name": input_data.collection_name,
            "top_k": input_data.top_k
        }

        result_state = await node.execute(state)

        if "error" in result_state.data:
            return RAGOutput(
                answer="",
                retrieved_documents=[],
                output_text="",
                success=False,
                error_message=result_state.data["error"]
            )

        return RAGOutput(
            answer=result_state.data.get("rag_answer", ""),
            retrieved_documents=result_state.data.get("retrieved_documents", []),
            query_embedding=result_state.data.get("query_embedding") if input_data.include_metadata else None,
            output_text=result_state.data.get("rag_answer", ""),
            data=result_state.data
        )

    except Exception as e:
        return RAGOutput(
            answer="",
            retrieved_documents=[],
            output_text="",
            success=False,
            error_message=str(e)
        )