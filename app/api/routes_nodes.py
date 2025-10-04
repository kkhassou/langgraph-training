from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Dict, Any

from app.nodes.llm_gemini import GeminiInput, gemini_node_handler
from app.nodes.ppt_ingest import ppt_ingest_handler
from app.nodes.mcp_integrations.slack_mcp_node import SlackMCPInput, slack_mcp_node_handler
from app.nodes.rag.rag_node import RAGInput, rag_node_handler
from app.nodes.rag.document_ingest_node import DocumentIngestInput, document_ingest_handler
from app.nodes.rag.search_node import SearchInput, search_node_handler
from app.nodes.rag.advanced_rag_node import AdvancedRAGInput, advanced_rag_handler


router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.get("/")
async def list_nodes():
    """List all available nodes and their capabilities"""
    return {
        "nodes": [
            {
                "name": "gemini",
                "description": "Generate responses using Google Gemini LLM",
                "endpoint": "/nodes/gemini",
                "method": "POST",
                "input_schema": {
                    "prompt": "string",
                    "temperature": "float (default: 0.7)",
                    "max_tokens": "int (default: 1000)"
                }
            },
            {
                "name": "ppt-ingest",
                "description": "Extract text from PowerPoint presentations",
                "endpoint": "/nodes/ppt-ingest",
                "method": "POST",
                "input_schema": {
                    "file": "multipart/form-data (PowerPoint file)"
                }
            },
            {
                "name": "slack-mcp",
                "description": "Interact with Slack via MCP integration",
                "endpoint": "/nodes/slack-mcp",
                "method": "POST",
                "input_schema": {
                    "action": "string (get_channels, send_message)",
                    "channel": "string (optional)",
                    "message": "string (optional)"
                }
            },
            {
                "name": "rag",
                "description": "Retrieve relevant documents and generate augmented response",
                "endpoint": "/nodes/rag",
                "method": "POST",
                "input_schema": {
                    "query": "string",
                    "collection_name": "string (default: default_collection)",
                    "top_k": "int (default: 5)",
                    "include_metadata": "bool (default: true)"
                }
            },
            {
                "name": "document-ingest",
                "description": "Process and store documents in vector database",
                "endpoint": "/nodes/document-ingest",
                "method": "POST",
                "input_schema": {
                    "content": "string",
                    "collection_name": "string (default: default_collection)",
                    "metadata": "object (default: {})",
                    "chunk_size": "int (optional)"
                }
            },
            {
                "name": "search",
                "description": "Advanced search with semantic, BM25, and hybrid options",
                "endpoint": "/nodes/search",
                "method": "POST",
                "input_schema": {
                    "query": "string",
                    "collection_name": "string (default: default_collection)",
                    "search_type": "string (default: hybrid) - options: semantic, bm25, hybrid",
                    "top_k": "int (default: 5)",
                    "filters": "object (optional)",
                    "semantic_weight": "float (default: 0.7)",
                    "bm25_weight": "float (default: 0.3)"
                }
            },
            {
                "name": "advanced-rag",
                "description": "Advanced RAG with context management and conversation history",
                "endpoint": "/nodes/advanced-rag",
                "method": "POST",
                "input_schema": {
                    "query": "string",
                    "collection_name": "string (default: default_collection)",
                    "search_type": "string (default: hybrid)",
                    "top_k": "int (default: 5)",
                    "include_conversation": "bool (default: true)",
                    "max_history_turns": "int (default: 3)",
                    "semantic_weight": "float (default: 0.7)",
                    "bm25_weight": "float (default: 0.3)",
                    "context_optimization": "bool (default: true)"
                }
            }
        ]
    }


@router.post("/gemini")
async def call_gemini_node(input_data: GeminiInput):
    """Execute Gemini LLM node"""
    try:
        result = await gemini_node_handler(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ppt-ingest")
async def call_ppt_ingest_node(file: UploadFile = File(...)):
    """Execute PowerPoint ingest node"""
    try:
        # Save uploaded file temporarily
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        try:
            result = await ppt_ingest_handler(temp_path)
            return result
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/slack-mcp")
async def call_slack_mcp_node(input_data: SlackMCPInput):
    """Execute Slack node via MCP server"""
    try:
        result = await slack_mcp_node_handler(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag")
async def call_rag_node(input_data: RAGInput):
    """Execute RAG (Retrieval-Augmented Generation) node"""
    try:
        result = await rag_node_handler(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/document-ingest")
async def call_document_ingest_node(input_data: DocumentIngestInput):
    """Execute document ingestion node"""
    try:
        result = await document_ingest_handler(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def call_search_node(input_data: SearchInput):
    """Execute advanced search node"""
    try:
        result = await search_node_handler(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/advanced-rag")
async def call_advanced_rag_node(input_data: AdvancedRAGInput):
    """Execute advanced RAG node with context management"""
    try:
        result = await advanced_rag_handler(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))