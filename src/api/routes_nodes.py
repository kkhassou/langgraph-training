from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Dict, Any

from src.nodes.llm.gemini import GeminiInput, gemini_node_handler
from src.nodes.document.ppt_ingest import ppt_ingest_handler
from src.nodes.integrations.mcp.slack import SlackMCPInput, slack_mcp_node_handler
from src.nodes.integrations.mcp.notion import NotionMCPInput, notion_mcp_node_handler
from src.nodes.integrations.mcp.gmail import GmailMCPInput, gmail_mcp_node_handler
from src.nodes.integrations.mcp.google_calendar import CalendarMCPInput, calendar_mcp_node_handler
from src.nodes.integrations.mcp.google_sheets import SheetsMCPInput, sheets_mcp_node_handler
from src.nodes.integrations.mcp.google_docs import DocsMCPInput, docs_mcp_node_handler
from src.nodes.integrations.mcp.google_slides import SlidesMCPInput, slides_mcp_node_handler
from src.nodes.integrations.mcp.google_forms import FormsMCPInput, forms_mcp_node_handler
from src.nodes.integrations.mcp.google_keep import KeepMCPInput, keep_mcp_node_handler
from src.nodes.integrations.mcp.google_apps_script import AppsScriptMCPInput, apps_script_mcp_node_handler
from src.nodes.integrations.mcp.vertex_ai import VertexAIMCPInput, vertex_ai_mcp_node_handler
from src.nodes.rag.rag_node import RAGInput, rag_node_handler
from src.nodes.rag.document_ingest_node import DocumentIngestInput, document_ingest_handler
from src.nodes.rag.search_node import SearchInput, search_node_handler
from src.nodes.rag.advanced_rag_node import AdvancedRAGInput, advanced_rag_handler


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
                "name": "notion-mcp",
                "description": "Interact with Notion via MCP integration",
                "endpoint": "/nodes/notion-mcp",
                "method": "POST",
                "input_schema": {
                    "action": "string (create_page, get_page, update_page, query_database, create_database_entry, search)",
                    "page_id": "string (optional, required for get_page/update_page)",
                    "parent_id": "string (optional, required for create_page)",
                    "database_id": "string (optional, required for query_database/create_database_entry)",
                    "title": "string (optional, for create_page/update_page)",
                    "content": "string (optional, for create_page)",
                    "filter": "object (optional, for query_database/search)",
                    "sorts": "array (optional, for query_database)",
                    "page_size": "int (optional, default: 10, for query_database)",
                    "properties": "object (optional, required for create_database_entry)",
                    "query": "string (optional, required for search)"
                }
            },
            {
                "name": "gmail-mcp",
                "description": "Interact with Gmail via MCP integration",
                "endpoint": "/nodes/gmail-mcp",
                "method": "POST",
                "input_schema": {
                    "action": "string (watch_inbox, get_messages, send_message)",
                    "topic_name": "string (optional, required for watch_inbox)",
                    "query": "string (optional, for get_messages)",
                    "max_results": "int (optional, default: 10)",
                    "to": "string (optional, required for send_message)",
                    "subject": "string (optional, required for send_message)",
                    "body": "string (optional, required for send_message)"
                }
            },
            {
                "name": "calendar-mcp",
                "description": "Interact with Google Calendar via MCP integration",
                "endpoint": "/nodes/calendar-mcp",
                "method": "POST",
                "input_schema": {
                    "action": "string (list_events, create_event, update_event, delete_event)",
                    "calendar_id": "string (optional, default: primary)",
                    "max_results": "int (optional, default: 10)",
                    "time_min": "string (optional, ISO 8601 format)",
                    "time_max": "string (optional, ISO 8601 format)",
                    "event_id": "string (optional, required for update/delete)",
                    "summary": "string (optional, event title)",
                    "start_time": "string (optional, ISO 8601 format)",
                    "end_time": "string (optional, ISO 8601 format)",
                    "description": "string (optional)",
                    "location": "string (optional)",
                    "attendees": "array of strings (optional, email addresses)"
                }
            },
            {
                "name": "sheets-mcp",
                "description": "Interact with Google Sheets via MCP integration",
                "endpoint": "/nodes/sheets-mcp",
                "method": "POST",
                "input_schema": {
                    "action": "string (create_spreadsheet, read_range, write_range, append_rows, clear_range, get_spreadsheet_info)",
                    "spreadsheet_id": "string (optional, required for most actions)",
                    "title": "string (optional, for create_spreadsheet)",
                    "range": "string (optional, A1 notation like 'Sheet1!A1:D10')",
                    "values": "array of arrays (optional, 2D array for write/append)"
                }
            },
            {
                "name": "docs-mcp",
                "description": "Interact with Google Docs via MCP integration",
                "endpoint": "/nodes/docs-mcp",
                "method": "POST",
                "input_schema": {
                    "action": "string (create_document, read_document, append_text, insert_text, replace_text)",
                    "document_id": "string (optional, required for most actions)",
                    "title": "string (optional, for create_document)",
                    "text": "string (optional, for text operations)",
                    "index": "int (optional, for insert_text)",
                    "find_text": "string (optional, for replace_text)",
                    "replace_text": "string (optional, for replace_text)",
                    "match_case": "bool (optional, for replace_text)"
                }
            },
            {
                "name": "slides-mcp",
                "description": "Interact with Google Slides via MCP integration",
                "endpoint": "/nodes/slides-mcp",
                "method": "POST",
                "input_schema": {
                    "action": "string (create_presentation, read_presentation, add_slide, add_text_to_slide, delete_slide)",
                    "presentation_id": "string (optional, required for most actions)",
                    "title": "string (optional, for create_presentation)",
                    "index": "int (optional, for add_slide)",
                    "slide_id": "string (optional, for add_text_to_slide/delete_slide)",
                    "text": "string (optional, for add_text_to_slide)"
                }
            },
            {
                "name": "forms-mcp",
                "description": "Interact with Google Forms via MCP integration",
                "endpoint": "/nodes/forms-mcp",
                "method": "POST",
                "input_schema": {
                    "action": "string (create_form, get_form, list_responses, get_response, update_form)",
                    "form_id": "string (optional, required for most actions)",
                    "title": "string (optional, for create_form/update_form)",
                    "description": "string (optional, for create_form/update_form)",
                    "response_id": "string (optional, required for get_response)"
                }
            },
            {
                "name": "keep-mcp",
                "description": "Interact with Google Keep via MCP integration",
                "endpoint": "/nodes/keep-mcp",
                "method": "POST",
                "input_schema": {
                    "action": "string (create_note, list_notes, get_note, update_note, delete_note)",
                    "note_id": "string (optional, required for get_note/update_note/delete_note)",
                    "title": "string (optional, for create_note/update_note)",
                    "body": "string (optional, required for create_note, optional for update_note)",
                    "page_size": "int (optional, default: 10, max: 100, for list_notes)"
                }
            },
            {
                "name": "apps-script-mcp",
                "description": "Interact with Google Apps Script via MCP integration",
                "endpoint": "/nodes/apps-script-mcp",
                "method": "POST",
                "input_schema": {
                    "action": "string (create_project, get_project, update_project, run_function, list_deployments)",
                    "script_id": "string (optional, required for most actions)",
                    "title": "string (optional, for create_project)",
                    "file_name": "string (optional, for update_project)",
                    "file_type": "string (optional, default: SERVER_JS, options: SERVER_JS, HTML, JSON)",
                    "source": "string (optional, for update_project)",
                    "function_name": "string (optional, for run_function)",
                    "parameters": "array (optional, for run_function)"
                }
            },
            {
                "name": "vertex-ai-mcp",
                "description": "Interact with Google Vertex AI via MCP integration",
                "endpoint": "/nodes/vertex-ai-mcp",
                "method": "POST",
                "input_schema": {
                    "action": "string (generate_text, chat, generate_embeddings, list_models)",
                    "prompt": "string (optional, required for generate_text)",
                    "message": "string (optional, required for chat)",
                    "model": "string (optional, default: gemini-1.5-flash)",
                    "temperature": "float (optional, default: 0.7, range: 0.0-2.0)",
                    "max_tokens": "int (optional, default: 1024)",
                    "history": "array (optional, for chat)",
                    "texts": "array of strings (optional, required for generate_embeddings)"
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


@router.post("/notion-mcp")
async def call_notion_mcp_node(input_data: NotionMCPInput):
    """Execute Notion node via MCP server"""
    try:
        result = await notion_mcp_node_handler(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gmail-mcp")
async def call_gmail_mcp_node(input_data: GmailMCPInput):
    """Execute Gmail node via MCP server"""
    try:
        result = await gmail_mcp_node_handler(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calendar-mcp")
async def call_calendar_mcp_node(input_data: CalendarMCPInput):
    """Execute Google Calendar node via MCP server"""
    try:
        result = await calendar_mcp_node_handler(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sheets-mcp")
async def call_sheets_mcp_node(input_data: SheetsMCPInput):
    """Execute Google Sheets node via MCP server"""
    try:
        result = await sheets_mcp_node_handler(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/docs-mcp")
async def call_docs_mcp_node(input_data: DocsMCPInput):
    """Execute Google Docs node via MCP server"""
    try:
        result = await docs_mcp_node_handler(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/slides-mcp")
async def call_slides_mcp_node(input_data: SlidesMCPInput):
    """Execute Google Slides node via MCP server"""
    try:
        result = await slides_mcp_node_handler(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/forms-mcp")
async def call_forms_mcp_node(input_data: FormsMCPInput):
    """Execute Google Forms node via MCP server"""
    try:
        result = await forms_mcp_node_handler(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/keep-mcp")
async def call_keep_mcp_node(input_data: KeepMCPInput):
    """Execute Google Keep node via MCP server"""
    try:
        result = await keep_mcp_node_handler(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apps-script-mcp")
async def call_apps_script_mcp_node(input_data: AppsScriptMCPInput):
    """Execute Google Apps Script node via MCP server"""
    try:
        result = await apps_script_mcp_node_handler(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vertex-ai-mcp")
async def call_vertex_ai_mcp_node(input_data: VertexAIMCPInput):
    """Execute Vertex AI node via MCP server"""
    try:
        result = await vertex_ai_mcp_node_handler(input_data)
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