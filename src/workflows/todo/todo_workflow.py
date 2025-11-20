"""TODO Workflow - Complete workflow for processing TODO emails

Flow:
1. Receive email → Parse TODOs
2. Split TODOs into individual items
3. Generate advice for each TODO (parallel)
4. Compose response email
5. Send response email
"""

from typing import Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, END
import logging
import asyncio

from src.nodes.todo.todo_parser import todo_parser_node
from src.nodes.todo.todo_advisor import todo_advisor_node
from src.nodes.todo.email_composer import email_composer_node
from src.services.mcp.gmail import GmailMCPService

logger = logging.getLogger(__name__)


class TodoWorkflowState(TypedDict, total=False):
    """State for TODO workflow"""
    email_content: str
    sender: str
    subject: str
    todos: List[Dict[str, Any]]
    todo_count: int
    advised_todos: List[Dict[str, Any]]
    email_subject: str
    email_body: str
    send_result: Any
    email_sent: bool
    send_error: str


async def parse_todos_step(state: TodoWorkflowState) -> TodoWorkflowState:
    """Step 1: Parse email content into TODOs"""
    logger.info("Step 1: Parsing TODOs from email")
    logger.info(f"State keys: {list(state.keys())}")
    logger.info(f"Full state: {state}")

    email_content = state.get("email_content", "")
    sender = state.get("sender", "")

    logger.info(f"Extracted - sender: '{sender}', content: '{email_content}'")

    result = await todo_parser_node.execute({
        "email_content": email_content,
        "sender": sender
    })

    if not result.success:
        raise ValueError(f"Failed to parse TODOs: {result.error}")

    state["todos"] = result.data.get("todos", [])
    state["todo_count"] = result.data.get("count", 0)
    logger.info(f"Parsed {state['todo_count']} TODOs")

    return state


async def advise_todos_step(state: TodoWorkflowState) -> TodoWorkflowState:
    """Step 2: Generate advice for all TODOs (parallel processing)"""
    logger.info("Step 2: Generating advice for TODOs")

    todos = state.get("todos", [])
    total = len(todos)

    if total == 0:
        logger.warning("No TODOs to advise")
        state["advised_todos"] = []
        return state

    # Process all TODOs in parallel
    tasks = []
    for idx, todo in enumerate(todos):
        task = todo_advisor_node.execute({
            "todo": todo,
            "index": idx,
            "total": total
        })
        tasks.append(task)

    # Wait for all advice to be generated
    results = await asyncio.gather(*tasks)

    # Collect successful results
    advised_todos = []
    for result in results:
        if result.success:
            advised_todos.append(result.data)
        else:
            logger.error(f"Failed to generate advice: {result.error}")

    state["advised_todos"] = advised_todos
    logger.info(f"Generated advice for {len(advised_todos)} TODOs")

    return state


async def compose_email_step(state: TodoWorkflowState) -> TodoWorkflowState:
    """Step 3: Compose response email"""
    logger.info("Step 3: Composing response email")

    advised_todos = state.get("advised_todos", [])
    recipient = state.get("sender", "")
    original_subject = state.get("subject", "TODO")

    result = await email_composer_node.execute({
        "advised_todos": advised_todos,
        "recipient": recipient,
        "original_subject": original_subject
    })

    if not result.success:
        raise ValueError(f"Failed to compose email: {result.error}")

    state["email_subject"] = result.data.get("subject", "")
    state["email_body"] = result.data.get("body", "")
    logger.info("Email composed successfully")

    return state


async def send_email_step(state: TodoWorkflowState) -> TodoWorkflowState:
    """Step 4: Send response email via Gmail"""
    logger.info("Step 4: Sending response email")

    recipient = state.get("sender", "")
    subject = state.get("email_subject", "")
    body = state.get("email_body", "")

    try:
        gmail_service = GmailMCPService()
        result = await gmail_service.send_message(
            to=recipient,
            subject=subject,
            body=body
        )

        state["send_result"] = result
        state["email_sent"] = True
        logger.info(f"Email sent successfully to {recipient}")

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        state["email_sent"] = False
        state["send_error"] = str(e)

    return state


def create_todo_workflow() -> StateGraph:
    """Create the TODO workflow graph"""

    # Create workflow graph
    workflow = StateGraph(TodoWorkflowState)

    # Add nodes
    workflow.add_node("parse_todos", parse_todos_step)
    workflow.add_node("advise_todos", advise_todos_step)
    workflow.add_node("compose_email", compose_email_step)
    workflow.add_node("send_email", send_email_step)

    # Define edges
    workflow.set_entry_point("parse_todos")
    workflow.add_edge("parse_todos", "advise_todos")
    workflow.add_edge("advise_todos", "compose_email")
    workflow.add_edge("compose_email", "send_email")
    workflow.add_edge("send_email", END)

    return workflow.compile()


# Create compiled workflow
todo_workflow = create_todo_workflow()


async def run_todo_workflow(
    email_content: str,
    sender: str,
    subject: str = "TODO"
) -> Dict[str, Any]:
    """
    Run the TODO workflow

    Args:
        email_content: Email content containing TODOs
        sender: Email sender address
        subject: Email subject

    Returns:
        Final workflow state
    """
    initial_state = {
        "email_content": email_content,
        "sender": sender,
        "subject": subject
    }

    logger.info(f"Starting TODO workflow with initial state: {initial_state}")
    print(f"[DEBUG] Initial state: {initial_state}")
    result = await todo_workflow.ainvoke(initial_state)
    logger.info(f"TODO workflow completed with result keys: {list(result.keys())}")
    print(f"[DEBUG] Result: {result}")

    return result
