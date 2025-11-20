from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import logging

from src.workflows.todo import run_todo_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])


class TodoWorkflowInput(BaseModel):
    """Input schema for TODO workflow"""
    email_content: str = Field(..., description="Email content containing TODOs")
    sender: str = Field(..., description="Email sender address")
    subject: str = Field(default="TODO", description="Email subject")


@router.get("/")
async def list_workflows():
    """List all available workflows"""
    return {
        "workflows": [
            {
                "name": "todo-workflow",
                "description": "Parse TODOs from email, generate advice, and send response",
                "endpoint": "/workflows/todo",
                "method": "POST",
                "input_schema": {
                    "email_content": "string (required) - Email content with TODO items",
                    "sender": "string (required) - Email sender address",
                    "subject": "string (optional, default: TODO) - Email subject"
                },
                "steps": [
                    "1. Parse TODOs from email using LLM",
                    "2. Generate advice for each TODO (parallel)",
                    "3. Compose response email with all advice",
                    "4. Send response email via Gmail"
                ]
            }
        ]
    }


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
