import json
import os
import pickle
from typing import List, Dict, Any, Optional
import numpy as np
from app.infrastructure.vector_stores.base import BaseVectorStore, Document, SearchResult


class LocalVectorStore(BaseVectorStore):
    """Simple local file-based vector store for development and testing"""

    def __init__(self, dimension: int = 768, data_dir: str = "vector_data"):
        super().__init__(dimension)
        self.data_dir = data_dir
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Ensure data directory exists"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def _get_collection_path(self, collection_name: str) -> str:
        """Get file path for collection"""
        return os.path.join(self.data_dir, f"{collection_name}.json")

    def _load_collection(self, collection_name: str) -> List[Dict[str, Any]]:
        """Load collection from file"""
        collection_path = self._get_collection_path(collection_name)
        if not os.path.exists(collection_path):
            return []
        
        try:
            with open(collection_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading collection {collection_name}: {str(e)}")
            return []

    def _save_collection(self, collection_name: str, documents: List[Dict[str, Any]]) -> bool:
        """Save collection to file"""
        collection_path = self._get_collection_path(collection_name)
        try:
            with open(collection_path, 'w', encoding='utf-8') as f:
                json.dump(documents, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving collection {collection_name}: {str(e)}")
            return False

    async def create_collection(self, collection_name: str) -> bool:
        """Create a new collection"""
        try:
            collection_path = self._get_collection_path(collection_name)
            if not os.path.exists(collection_path):
                # Create empty collection file
                with open(collection_path, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                print(f"Created collection: {collection_name}")
            else:
                print(f"Collection {collection_name} already exists")
            return True
        except Exception as e:
            print(f"Error creating collection {collection_name}: {str(e)}")
            return False

    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection"""
        try:
            collection_path = self._get_collection_path(collection_name)
            if os.path.exists(collection_path):
                os.remove(collection_path)
                print(f"Deleted collection: {collection_name}")
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
            # Load existing documents
            existing_docs = self._load_collection(collection_name)
            
            # Convert new documents to dict format
            for doc in documents:
                doc_dict = {
                    'id': doc.id,
                    'content': doc.content,
                    'metadata': doc.metadata,
                    'embedding': doc.embedding
                }
                existing_docs.append(doc_dict)
            
            # Save updated collection
            success = self._save_collection(collection_name, existing_docs)
            if success:
                print(f"Added {len(documents)} documents to collection {collection_name}")
            return success

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
            # Load documents
            documents = self._load_collection(collection_name)
            
            search_results = []
            for i, doc_dict in enumerate(documents):
                # Apply metadata filters if provided
                if filter_metadata:
                    match = True
                    for key, value in filter_metadata.items():
                        if key not in doc_dict.get('metadata', {}) or doc_dict['metadata'][key] != value:
                            match = False
                            break
                    if not match:
                        continue

                if doc_dict.get('embedding'):
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(query_embedding, doc_dict['embedding'])

                    document = Document(
                        id=doc_dict['id'],
                        content=doc_dict['content'],
                        metadata=doc_dict.get('metadata', {}),
                        embedding=doc_dict['embedding']
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
            documents = self._load_collection(collection_name)
            
            # Filter out documents to delete
            filtered_docs = [doc for doc in documents if doc['id'] not in document_ids]
            
            success = self._save_collection(collection_name, filtered_docs)
            if success:
                deleted_count = len(documents) - len(filtered_docs)
                print(f"Deleted {deleted_count} documents from collection {collection_name}")
            return success

        except Exception as e:
            print(f"Error deleting documents from {collection_name}: {str(e)}")
            return False

    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get collection information"""
        try:
            documents = self._load_collection(collection_name)
            return {
                "name": collection_name,
                "document_count": len(documents),
                "dimension": self.dimension,
                "storage": "local_file"
            }
        except Exception as e:
            return {
                "name": collection_name,
                "error": str(e),
                "document_count": 0,
                "dimension": self.dimension,
                "storage": "local_file"
            }

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            # Convert to numpy arrays for efficient computation
            a = np.array(vec1)
            b = np.array(vec2)
            
            # Calculate cosine similarity
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            return dot_product / (norm_a * norm_b)
        except Exception:
            # Fallback to manual calculation
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = sum(a * a for a in vec1) ** 0.5
            magnitude2 = sum(a * a for a in vec2) ** 0.5
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)

    def get_info(self) -> Dict[str, Any]:
        """Get vector store information"""
        info = super().get_info()
        info.update({
            "database": "Local JSON files",
            "data_directory": self.data_dir,
            "similarity_metric": "cosine",
            "supports_metadata_filter": True,
            "storage_format": "JSON"
        })
        return info
