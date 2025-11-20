from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import tempfile
import os
import logging

from src.workflows.basic import SimpleChatGraph, SimpleChatInput
from src.workflows.basic import PPTSummaryGraph, PPTSummaryInput
from src.workflows.rag import RAGWorkflow, RAGWorkflowInput
from src.workflows.patterns import ReflectionGraph, ReflectionInput
from src.workflows.patterns import ChainOfThoughtGraph, ChainOfThoughtInput
from src.workflows.todo import run_todo_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])

# Initialize workflow instances
simple_chat_graph = SimpleChatGraph()
ppt_summary_graph = PPTSummaryGraph()
rag_workflow = RAGWorkflow()
reflection_graph = ReflectionGraph()
chain_of_thought_graph = ChainOfThoughtGraph()


# ============================================================================
# Basic Workflows
# ============================================================================

@router.post("/simple-chat")
async def run_simple_chat(input_data: SimpleChatInput):
    """Run simple chat workflow using Gemini LLM"""
    try:
        result = await simple_chat_graph.run(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ppt-summary")
async def run_ppt_summary(file: UploadFile = File(...), summary_style: str = "bullet_points"):
    """Run PowerPoint summary workflow"""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        try:
            input_data = PPTSummaryInput(
                file_path=temp_path,
                summary_style=summary_style
            )
            result = await ppt_summary_graph.run(input_data)
            return result
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Pattern Workflows
# ============================================================================

@router.post("/reflection")
async def run_reflection(input_data: ReflectionInput):
    """Run reflection pattern workflow for iterative improvement"""
    try:
        result = await reflection_graph.run(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chain-of-thought")
async def run_chain_of_thought(input_data: ChainOfThoughtInput):
    """Run Chain of Thought pattern workflow for step-by-step reasoning"""
    try:
        result = await chain_of_thought_graph.run(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# RAG Workflow
# ============================================================================

@router.post("/rag")
async def run_rag_workflow(input_data: RAGWorkflowInput):
    """Run RAG workflow with multiple search strategies"""
    try:
        result = await rag_workflow.run(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TODO Workflow
# ============================================================================

class TodoWorkflowInput(BaseModel):
    """Input schema for TODO workflow"""
    email_content: str = Field(..., description="Email content containing TODOs")
    sender: str = Field(..., description="Email sender address")
    subject: str = Field(default="TODO", description="Email subject")


@router.post("/todo")
async def execute_todo_workflow(input_data: TodoWorkflowInput):
    """
    Execute TODO workflow
    
    This workflow:
    1. Parses TODOs from email content using LLM
    2. Generates advice for each TODO item in parallel
    3. Composes a response email with all advice
    4. Sends the response email back to the sender
    """
    try:
        logger.info(f"Starting TODO workflow for sender: {input_data.sender}")
        
        result = await run_todo_workflow(
            email_content=input_data.email_content,
            sender=input_data.sender,
            subject=input_data.subject
        )
        
        # Extract key information from result
        response = {
            "success": result.get("email_sent", False),
            "todo_count": result.get("todo_count", 0),
            "sender": result.get("sender", ""),
            "email_subject": result.get("email_subject", ""),
            "email_sent": result.get("email_sent", False)
        }
        
        if not result.get("email_sent"):
            response["error"] = result.get("send_error", "Unknown error")
        
        return response
    
    except Exception as e:
        logger.error(f"Error executing TODO workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/todo/preview")
async def preview_todo_workflow(input_data: TodoWorkflowInput):
    """
    Preview TODO workflow without sending email
    
    This endpoint executes the workflow up to email composition
    and returns the email content without actually sending it.
    Useful for testing and debugging.
    """
    try:
        logger.info(f"Previewing TODO workflow for sender: {input_data.sender}")
        
        from src.workflows.todo import (
            parse_todos_step,
            advise_todos_step,
            compose_email_step
        )
        
        # Execute workflow steps without sending
        state = {
            "email_content": input_data.email_content,
            "sender": input_data.sender,
            "subject": input_data.subject
        }
        
        # Step 1: Parse TODOs
        state = await parse_todos_step(state)
        
        # Step 2: Generate advice
        state = await advise_todos_step(state)
        
        # Step 3: Compose email
        state = await compose_email_step(state)
        
        # Return preview
        return {
            "success": True,
            "todo_count": state.get("todo_count", 0),
            "todos": state.get("todos", []),
            "advised_todos": state.get("advised_todos", []),
            "email_subject": state.get("email_subject", ""),
            "email_body": state.get("email_body", ""),
            "preview_mode": True
        }
    
    except Exception as e:
        logger.error(f"Error previewing TODO workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Workflow Visualization
# ============================================================================

@router.get("/diagrams/{workflow_name}")
async def get_workflow_diagram(workflow_name: str):
    """Get Mermaid diagram for a specific workflow"""
    try:
        diagrams = {
            "simple-chat": simple_chat_graph.get_mermaid_diagram(),
            "ppt-summary": ppt_summary_graph.get_mermaid_diagram(),
            "rag": rag_workflow.get_mermaid_diagram(),
            "reflection": reflection_graph.get_mermaid_diagram(),
            "chain-of-thought": chain_of_thought_graph.get_mermaid_diagram()
        }
        
        if workflow_name not in diagrams:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")
        
        return {
            "workflow_name": workflow_name,
            "mermaid_diagram": diagrams[workflow_name]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Workflow Listing
# ============================================================================

@router.get("/")
async def list_workflows():
    """List all available workflows"""
    return {
        "workflows": [
            {
                "name": "simple-chat",
                "endpoint": "/workflows/simple-chat",
                "description": "Simple chat workflow using Gemini LLM",
                "method": "POST",
                "category": "basic"
            },
            {
                "name": "ppt-summary",
                "endpoint": "/workflows/ppt-summary",
                "description": "PowerPoint summarization workflow",
                "method": "POST",
                "category": "basic"
            },
            {
                "name": "reflection",
                "endpoint": "/workflows/reflection",
                "description": "Reflection pattern for iterative improvement",
                "method": "POST",
                "category": "pattern"
            },
            {
                "name": "chain-of-thought",
                "endpoint": "/workflows/chain-of-thought",
                "description": "Chain of Thought reasoning pattern",
                "method": "POST",
                "category": "pattern"
            },
            {
                "name": "rag",
                "endpoint": "/workflows/rag",
                "description": "Advanced RAG workflow with multiple strategies",
                "method": "POST",
                "category": "advanced"
            },
            {
                "name": "todo",
                "endpoint": "/workflows/todo",
                "description": "Parse TODOs from email, generate advice, and send response",
                "method": "POST",
                "category": "advanced",
                "steps": [
                    "1. Parse TODOs from email using LLM",
                    "2. Generate advice for each TODO (parallel)",
                    "3. Compose response email with all advice",
                    "4. Send response email via Gmail"
                ]
            }
        ]
    }
