from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Dict, Any

from app.nodes.llm_gemini import GeminiInput, gemini_node_handler
from app.nodes.ppt_ingest import ppt_ingest_handler
from app.nodes.mcp_integrations.slack_mcp_node import SlackMCPInput, slack_mcp_node_handler


router = APIRouter(prefix="/nodes", tags=["nodes"])


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