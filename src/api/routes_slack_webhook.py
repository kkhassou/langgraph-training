"""Slack Webhook Routes - Handle Slack events and interactions"""

from fastapi import APIRouter, Request, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import logging
import hmac
import hashlib
import time
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slack", tags=["slack-webhook"])


class SlackEventPayload(BaseModel):
    """Slack Event API payload"""
    type: str
    event: Optional[Dict[str, Any]] = None
    challenge: Optional[str] = None  # For URL verification
    token: Optional[str] = None
    team_id: Optional[str] = None
    api_app_id: Optional[str] = None


def verify_slack_signature(
    body: bytes,
    timestamp: str,
    signature: str,
    signing_secret: str
) -> bool:
    """Verify that the request came from Slack"""
    # Prevent replay attacks
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False

    # Create signature
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    my_signature = 'v0=' + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(my_signature, signature)


@router.post("/events")
async def slack_events(
    request: Request,
    x_slack_request_timestamp: str = Header(None),
    x_slack_signature: str = Header(None)
):
    """
    Slack Events API endpoint

    Handles:
    - URL verification challenge
    - Message events
    - App mentions
    - Other Slack events
    """
    try:
        # Get raw body for signature verification
        body = await request.body()

        # Verify Slack signature if signing secret is configured
        signing_secret = os.getenv("SLACK_SIGNING_SECRET")
        if signing_secret and x_slack_request_timestamp and x_slack_signature:
            if not verify_slack_signature(
                body,
                x_slack_request_timestamp,
                x_slack_signature,
                signing_secret
            ):
                raise HTTPException(status_code=403, detail="Invalid signature")

        # Parse JSON payload
        payload = await request.json()

        # Handle URL verification challenge
        if payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge")}

        # Handle event callback
        if payload.get("type") == "event_callback":
            event = payload.get("event", {})
            event_type = event.get("type")

            logger.info(f"Received Slack event: {event_type}")

            # Ignore bot messages to prevent loops
            if event.get("bot_id"):
                return {"ok": True}

            # Handle app mentions
            if event_type == "app_mention":
                await handle_app_mention(event)

            # Handle direct messages
            elif event_type == "message" and event.get("channel_type") == "im":
                await handle_direct_message(event)

            # Handle channel messages with specific patterns
            elif event_type == "message":
                await handle_channel_message(event)

            return {"ok": True}

        return {"ok": True}

    except Exception as e:
        logger.error(f"Error handling Slack event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_app_mention(event: Dict[str, Any]):
    """Handle @app mentions in channels"""
    text = event.get("text", "")
    channel = event.get("channel")
    user = event.get("user")

    logger.info(f"App mentioned by {user} in {channel}: {text}")

    # TODO: Process the mention and respond
    # Example: Trigger TODO workflow if message contains TODO items
    if "TODO" in text.upper() or "タスク" in text:
        from src.workflows.todo_workflow import run_todo_workflow

        # Extract user email (would need to fetch from Slack API)
        user_email = f"{user}@example.com"  # Placeholder

        try:
            result = await run_todo_workflow(
                email_content=text,
                sender=user_email,
                subject="Slack TODO Request"
            )

            logger.info(f"TODO workflow completed: {result.get('todo_count')} todos processed")
        except Exception as e:
            logger.error(f"Error running TODO workflow: {e}")


async def handle_direct_message(event: Dict[str, Any]):
    """Handle direct messages to the bot"""
    text = event.get("text", "")
    user = event.get("user")
    channel = event.get("channel")

    logger.info(f"Direct message from {user}: {text}")

    # TODO: Implement DM handling logic
    # Could trigger different workflows based on message content


async def handle_channel_message(event: Dict[str, Any]):
    """Handle regular channel messages"""
    text = event.get("text", "")
    channel = event.get("channel")

    # Only process if message matches certain patterns
    # For example, messages starting with specific keywords
    if text.startswith("!todo") or text.startswith("!タスク"):
        logger.info(f"TODO trigger detected in channel {channel}")
        # Process as TODO request


@router.post("/interactions")
async def slack_interactions(request: Request):
    """
    Handle Slack interactive components

    Handles:
    - Button clicks
    - Menu selections
    - Dialog submissions
    """
    try:
        # Slack sends interaction payloads as form data
        form_data = await request.form()
        payload = form_data.get("payload")

        if not payload:
            raise HTTPException(status_code=400, detail="No payload found")

        import json
        payload_data = json.loads(payload)

        interaction_type = payload_data.get("type")
        logger.info(f"Received Slack interaction: {interaction_type}")

        # Handle different interaction types
        if interaction_type == "block_actions":
            # Button click or menu selection
            actions = payload_data.get("actions", [])
            for action in actions:
                action_id = action.get("action_id")
                logger.info(f"Action triggered: {action_id}")
                # Process action

        elif interaction_type == "view_submission":
            # Modal form submission
            view = payload_data.get("view", {})
            logger.info(f"View submitted: {view.get('callback_id')}")
            # Process submission

        return {"ok": True}

    except Exception as e:
        logger.error(f"Error handling Slack interaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/commands")
async def slack_slash_commands(request: Request):
    """
    Handle Slack slash commands

    Example: /todo <task description>
    """
    try:
        form_data = await request.form()

        command = form_data.get("command")
        text = form_data.get("text", "")
        user_id = form_data.get("user_id")
        channel_id = form_data.get("channel_id")

        logger.info(f"Slash command received: {command} from {user_id}")

        # Handle different commands
        if command == "/todo":
            # Trigger TODO workflow
            return {
                "response_type": "ephemeral",
                "text": f"Processing your TODO: {text}"
            }

        return {
            "response_type": "ephemeral",
            "text": "Command not recognized"
        }

    except Exception as e:
        logger.error(f"Error handling slash command: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def slack_webhook_health():
    """Health check endpoint for Slack webhook"""
    return {
        "status": "healthy",
        "service": "slack-webhook",
        "signing_secret_configured": bool(os.getenv("SLACK_SIGNING_SECRET"))
    }
