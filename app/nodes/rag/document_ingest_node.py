from typing import Dict, Any, List
import uuid
from pydantic import BaseModel
from app.nodes.base_node import BaseNode, NodeState, NodeInput, NodeOutput
from app.infrastructure.embeddings.gemini import GeminiEmbeddingProvider
from app.infrastructure.vector_stores.supabase import SupabaseVectorStore, Document
from app.infrastructure.vector_stores.local import LocalVectorStore
from app.core.config import settings


class DocumentIngestInput(NodeInput):
    """Input model for document ingestion"""
    content: str
    collection_name: str = "default_collection"
    metadata: Dict[str, Any] = {}
    chunk_size: int = None  # Use default if not specified


class DocumentIngestOutput(NodeOutput):
    """Output model for document ingestion"""
    document_id: str = ""
    chunks_created: int = 0
    collection_name: str = ""
    
    # Ensure output_text is populated for compatibility with NodeOutput
    def __init__(self, **data):
        if 'output_text' not in data:
            # Create a meaningful output message based on the ingestion result
            if data.get('success', True) and data.get('chunks_created', 0) > 0:
                data['output_text'] = f"文書の取り込みが完了しました。{data.get('chunks_created', 0)}個のチャンクが作成され、コレクション '{data.get('collection_name', '')}' に保存されました。"
            elif not data.get('success', True):
                data['output_text'] = f"文書の取り込みに失敗しました: {data.get('error_message', '不明なエラー')}"
            else:
                data['output_text'] = "文書の取り込み処理が完了しました。"
        super().__init__(**data)


class DocumentIngestNode(BaseNode):
    """Node for ingesting documents into vector store"""

    def __init__(self):
        super().__init__(
            name="document_ingest",
            description="Process and store documents in vector database"
        )
        self.embedding_provider = None
        self.vector_store = None

    def _initialize_components(self):
        """Initialize components lazily"""
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

    async def execute(self, state: NodeState) -> NodeState:
        """Execute document ingestion"""
        try:
            self._initialize_components()

            # Get input data
            content = state.data.get("content", "")
            collection_name = state.data.get("collection_name", "default_collection")
            metadata = state.data.get("metadata", {})
            chunk_size = state.data.get("chunk_size", settings.max_chunk_size)

            if not content:
                state.data["error"] = "Content is required for document ingestion"
                return state

            # Step 1: Create collection if it doesn't exist
            await self.vector_store.create_collection(collection_name)

            # Step 2: Split content into chunks
            chunks = self._split_text(content, chunk_size, settings.chunk_overlap)

            # Step 3: Generate embeddings and create documents
            documents = []
            document_id = str(uuid.uuid4())

            for i, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_chunk_{i}"

                # Generate embedding for chunk
                embedding = await self.embedding_provider.embed_text(chunk)

                # Create document with metadata
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "parent_document_id": document_id,
                    "chunk_index": i,
                    "chunk_count": len(chunks)
                })

                document = Document(
                    id=chunk_id,
                    content=chunk,
                    metadata=chunk_metadata,
                    embedding=embedding
                )
                documents.append(document)

            # Step 4: Store documents in vector store
            success = await self.vector_store.add_documents(collection_name, documents)

            if success:
                state.data.update({
                    "document_id": document_id,
                    "chunks_created": len(chunks),
                    "collection_name": collection_name,
                    "ingestion_success": True
                })
            else:
                state.data["error"] = "Failed to store documents in vector database"

            state.metadata["node"] = self.name
            state.metadata["chunks_processed"] = len(chunks)

            return state

        except Exception as e:
            state.data["error"] = f"Document ingestion failed: {str(e)}"
            state.metadata["error_node"] = self.name
            return state

    def _split_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into chunks with overlap"""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            # Calculate end position
            end = start + chunk_size

            # If this is not the last chunk, try to break at a sentence boundary
            if end < len(text):
                # Look for sentence endings within the last 100 characters
                search_start = max(end - 100, start + chunk_size // 2)
                sentence_end = -1

                for i in range(end - 1, search_start - 1, -1):
                    if text[i] in '.!?。！？':
                        sentence_end = i + 1
                        break

                if sentence_end > 0:
                    end = sentence_end

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position with overlap
            start = end - overlap
            if start >= len(text):
                break

        return chunks


async def document_ingest_handler(input_data: DocumentIngestInput) -> DocumentIngestOutput:
    """Standalone handler for document ingestion API endpoint"""
    try:
        node = DocumentIngestNode()
        state = NodeState()
        state.data = {
            "content": input_data.content,
            "collection_name": input_data.collection_name,
            "metadata": input_data.metadata,
            "chunk_size": input_data.chunk_size or settings.max_chunk_size
        }

        result_state = await node.execute(state)

        if "error" in result_state.data:
            return DocumentIngestOutput(
                output_text=f"文書の取り込みに失敗しました: {result_state.data['error']}",
                success=False,
                error_message=result_state.data["error"]
            )

        return DocumentIngestOutput(
            document_id=result_state.data.get("document_id", ""),
            chunks_created=result_state.data.get("chunks_created", 0),
            collection_name=result_state.data.get("collection_name", ""),
            output_text=f"文書の取り込みが完了しました。{result_state.data.get('chunks_created', 0)}個のチャンクが作成され、コレクション '{result_state.data.get('collection_name', '')}' に保存されました。",
            data=result_state.data
        )

    except Exception as e:
        return DocumentIngestOutput(
            output_text=f"文書の取り込みに失敗しました: {str(e)}",
            success=False,
            error_message=str(e)
        )