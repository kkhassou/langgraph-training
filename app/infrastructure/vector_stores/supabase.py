from typing import List, Dict, Any, Optional
import asyncio
from supabase import create_client, Client
from app.infrastructure.vector_stores.base import BaseVectorStore, Document, SearchResult
from app.core.config import settings


class SupabaseVectorStore(BaseVectorStore):
    """Supabase vector store implementation using pgvector"""

    def __init__(self, dimension: int = 768):
        super().__init__(dimension)
        self.client = self._initialize_client()

    def _initialize_client(self) -> Client:
        """Initialize Supabase client"""
        if not settings.supabase_url or not settings.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY are required")

        return create_client(settings.supabase_url, settings.supabase_key)

    async def create_collection(self, collection_name: str) -> bool:
        """Check if collection exists (table must be created manually in Supabase)"""
        try:
            # Test if table exists by attempting a simple query
            result = self.client.table(collection_name).select("id").limit(1).execute()
            print(f"Collection {collection_name} exists and is accessible")
            return True
        except Exception as e:
            print(f"Collection {collection_name} doesn't exist or is not accessible: {str(e)}")
            print(f"Please create the table manually in Supabase SQL Editor:")
            print(f"""
CREATE TABLE IF NOT EXISTS {collection_name} (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{{}}',
    embedding vector({self.dimension}),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS {collection_name}_embedding_idx
ON {collection_name}
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
            """)
            return False

    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection (drop table)"""
        try:
            drop_sql = f"DROP TABLE IF EXISTS {collection_name};"
            result = self.client.rpc('exec_sql', {'sql': drop_sql}).execute()
            return True
        except Exception as e:
            print(f"Error deleting collection {collection_name}: {str(e)}")
            return False

    async def add_documents(
        self,
        collection_name: str,
        documents: List[Document]
    ) -> bool:
        """Add documents to collection"""
        try:
            # Prepare data for insertion
            rows = []
            for doc in documents:
                row = {
                    'id': doc.id,
                    'content': doc.content,
                    'metadata': doc.metadata,
                    'embedding': doc.embedding
                }
                rows.append(row)

            # Insert documents
            result = self.client.table(collection_name).insert(rows).execute()
            return len(result.data) == len(documents)

        except Exception as e:
            print(f"Error adding documents to {collection_name}: {str(e)}")
            return False

    async def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar documents using cosine similarity"""
        try:
            # Build the query
            query = self.client.table(collection_name).select(
                "id, content, metadata, embedding"
            )

            # Apply metadata filters if provided
            if filter_metadata:
                for key, value in filter_metadata.items():
                    query = query.filter(f"metadata->{key}", "eq", value)

            # Execute the query (note: vector similarity needs to be handled differently)
            # For now, get all documents and calculate similarity in Python
            # In production, use pgvector's similarity functions
            result = query.limit(100).execute()  # Limit for performance

            search_results = []
            for i, row in enumerate(result.data):
                if row['embedding']:
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(query_embedding, row['embedding'])

                    document = Document(
                        id=row['id'],
                        content=row['content'],
                        metadata=row['metadata'],
                        embedding=row['embedding']
                    )

                    search_results.append(SearchResult(
                        document=document,
                        score=similarity,
                        rank=i
                    ))

            # Sort by similarity score and return top_k
            search_results.sort(key=lambda x: x.score, reverse=True)
            return search_results[:top_k]

        except Exception as e:
            print(f"Error searching in {collection_name}: {str(e)}")
            return []

    async def delete_documents(
        self,
        collection_name: str,
        document_ids: List[str]
    ) -> bool:
        """Delete documents by IDs"""
        try:
            result = self.client.table(collection_name).delete().in_('id', document_ids).execute()
            return True
        except Exception as e:
            print(f"Error deleting documents from {collection_name}: {str(e)}")
            return False

    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get collection information"""
        try:
            # Get table statistics
            count_result = self.client.table(collection_name).select(
                "id", count="exact"
            ).execute()

            return {
                "name": collection_name,
                "document_count": count_result.count,
                "dimension": self.dimension
            }
        except Exception as e:
            return {
                "name": collection_name,
                "error": str(e),
                "document_count": 0,
                "dimension": self.dimension
            }

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            import math
            
            # Handle Supabase pgvector format conversion
            def normalize_vector(vec):
                if isinstance(vec, str):
                    # Parse string representation of vector
                    import json
                    return json.loads(vec)
                elif hasattr(vec, '__iter__') and not isinstance(vec, str):
                    # Convert to float list
                    return [float(x) for x in vec]
                else:
                    return vec
            
            v1 = normalize_vector(vec1)
            v2 = normalize_vector(vec2)
            
            if len(v1) != len(v2):
                print(f"Vector dimension mismatch: {len(v1)} vs {len(v2)}")
                return 0.0
            
            # Calculate dot product and magnitudes with explicit float conversion
            dot_product = sum(float(a) * float(b) for a, b in zip(v1, v2))
            magnitude1 = math.sqrt(sum(float(a) * float(a) for a in v1))
            magnitude2 = math.sqrt(sum(float(b) * float(b) for b in v2))

            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0

            similarity = dot_product / (magnitude1 * magnitude2)
            return float(similarity)
            
        except Exception as e:
            print(f"Cosine similarity error: {str(e)}")
            print(f"vec1 type: {type(vec1)}, sample: {str(vec1)[:100] if hasattr(vec1, '__iter__') else vec1}")
            print(f"vec2 type: {type(vec2)}, sample: {str(vec2)[:100] if hasattr(vec2, '__iter__') else vec2}")
            import traceback
            traceback.print_exc()
            return 0.0

    def get_info(self) -> Dict[str, Any]:
        """Get vector store information"""
        info = super().get_info()
        info.update({
            "database": "Supabase PostgreSQL",
            "extension": "pgvector",
            "similarity_metric": "cosine",
            "supports_metadata_filter": True
        })
        return info