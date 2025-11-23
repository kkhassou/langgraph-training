from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from typing import Dict, Any

# ✅ 新しい構造からのインポート
from src.nodes.blocks.llm import LLMInput, llm_node_handler, LLMNode
from src.nodes.io.loader import LoaderInput, ppt_ingest_handler
from src.nodes.tools.slack import SlackInput, slack_node_handler
from src.nodes.blocks.retrieval import RetrievalInput, retrieval_node_handler

# Dependencies
from src.api.dependencies import get_llm_node, get_llm_provider
from src.core.providers.llm import LLMProvider

# ⚠️ 以下の統合は現在リファクタリング中または削除されました
# from src.nodes.integrations.notion import NotionInput, notion_node_handler
# from src.nodes.integrations.github import GitHubInput, github_node_handler
# from src.nodes.integrations.google.gmail import GmailInput, gmail_node_handler
# from src.nodes.integrations.google.calendar import GoogleCalendarInput, calendar_node_handler
# from src.nodes.integrations.google.sheets import GoogleSheetsInput, sheets_node_handler
# from src.nodes.integrations.google.docs import GoogleDocsInput, docs_node_handler
# from src.nodes.integrations.google.slides import GoogleSlidesInput, slides_node_handler
# from src.nodes.integrations.google.forms import GoogleFormsInput, forms_node_handler
# from src.nodes.integrations.google.keep import GoogleKeepInput, keep_node_handler
# from src.nodes.integrations.google.apps_script import GoogleAppsScriptInput, apps_script_node_handler
# from src.nodes.integrations.google.vertex_ai import VertexAiInput, vertex_ai_node_handler
# from src.nodes.rag.document_ingest_node import DocumentIngestInput, document_ingest_handler
# from src.nodes.rag.search_node import SearchInput, search_node_handler
# from src.nodes.rag.advanced_rag_node import AdvancedRAGInput, advanced_rag_handler


router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.get("/")
async def list_nodes():
    """List all available nodes and their capabilities"""
    return {
        "nodes": [
            {
                "name": "llm",
                "description": "Generate responses using LLM (Generic)",
                "endpoint": "/nodes/llm",
                "method": "POST",
                "input_schema": {
                    "prompt": "string",
                    "temperature": "float (default: 0.7)",
                    "max_tokens": "int (default: 1000)"
                }
            },
            {
                "name": "loader",
                "description": "Load content from files (Generic)",
                "endpoint": "/nodes/loader",
                "method": "POST",
                "input_schema": {
                    "file_path": "string"
                }
            },
            {
                "name": "slack",
                "description": "Interact with Slack",
                "endpoint": "/nodes/slack",
                "method": "POST",
                "input_schema": {
                    "action": "string (send_message, get_channels, etc.)",
                    "channel": "string",
                    "text": "string"
                }
            },
            {
                "name": "retrieval",
                "description": "Retrieve documents from knowledge base",
                "endpoint": "/nodes/retrieval",
                "method": "POST",
                "input_schema": {
                    "query": "string",
                    "collection_name": "string",
                    "top_k": "int"
                }
            }
        ]
    }


@router.post("/llm")
async def run_llm_node(
    input_data: LLMInput,
    provider: LLMProvider = Depends(get_llm_provider)
):
    """Run generic LLM node
    
    依存性注入により、LLMProviderが自動的に提供されます。
    テスト時には異なるプロバイダーを注入できます。
    """
    # ノードハンドラーに依存性を渡して実行
    result = await llm_node_handler(input_data, provider=provider)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error_message)
    return result


# 後方互換性エイリアス
@router.post("/gemini")
async def run_gemini_node(
    input_data: LLMInput,
    provider: LLMProvider = Depends(get_llm_provider)
):
    """Run Gemini node (Alias for LLM node)
    
    依存性注入により、LLMProviderが自動的に提供されます。
    """
    return await run_llm_node(input_data, provider)


@router.post("/loader")
async def run_loader_node(input_data: LoaderInput):
    """Run generic loader node"""
    # Currently reusing ppt handler logic for simplicity, but should be generic
    return await ppt_ingest_handler(input_data.file_path)


# 後方互換性エイリアス
@router.post("/ppt-ingest")
async def run_ppt_ingest_node(file_path: str):
    """Run PowerPoint ingest node (Alias for Loader node)"""
    return await ppt_ingest_handler(file_path)


@router.post("/slack")
async def run_slack_node(input_data: SlackInput):
    """Run Slack node"""
    result = await slack_node_handler(input_data)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error_message)
    return result


@router.post("/retrieval")
async def run_retrieval_node(input_data: RetrievalInput):
    """Run Retrieval node"""
    result = await retrieval_node_handler(input_data)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error_message)
    return result


# 後方互換性エイリアス
@router.post("/rag")
async def run_rag_node(input_data: RetrievalInput):
    """Run RAG node (Alias for Retrieval node)"""
    return await run_retrieval_node(input_data)
