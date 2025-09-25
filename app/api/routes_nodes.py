from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Dict, Any

from app.nodes.llm_gemini import GeminiInput, gemini_node_handler
from app.nodes.ppt_ingest import ppt_ingest_handler
from app.nodes.slack_node import SlackInput, slack_node_handler
from app.nodes.jira_node import JiraInput, jira_node_handler

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


@router.post("/slack")
async def call_slack_node(input_data: SlackInput):
    """Execute Slack node"""
    try:
        result = await slack_node_handler(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jira")
async def call_jira_node(input_data: JiraInput):
    """Execute Jira node"""
    try:
        result = await jira_node_handler(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_nodes():
    """List available nodes"""
    return {
        "available_nodes": [
            {
                "name": "gemini",
                "endpoint": "/nodes/gemini",
                "description": "Generate responses using Google Gemini LLM",
                "method": "POST"
            },
            {
                "name": "ppt-ingest",
                "endpoint": "/nodes/ppt-ingest",
                "description": "Extract text content from PowerPoint presentations",
                "method": "POST"
            },
            {
                "name": "slack",
                "endpoint": "/nodes/slack",
                "description": "Interact with Slack API for messages and channels",
                "method": "POST"
            },
            {
                "name": "jira",
                "endpoint": "/nodes/jira",
                "description": "Interact with Jira API for issue management",
                "method": "POST"
            }
        ]
    }