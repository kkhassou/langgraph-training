"""Slack Slash Commands - Extended handlers for specific commands"""

from fastapi import APIRouter, Request, BackgroundTasks
from typing import Dict, Any
import logging
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slack/cmd", tags=["slack-commands"])


async def send_delayed_response(response_url: str, message: Dict[str, Any]):
    """Send a delayed response to Slack using response_url"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(response_url, json=message)
            response.raise_for_status()
            logger.info(f"Delayed response sent successfully")
    except Exception as e:
        logger.error(f"Error sending delayed response: {e}")


@router.post("/todo")
async def handle_todo_command(request: Request, background_tasks: BackgroundTasks):
    """
    Handle /todo slash command

    Triggers TODO workflow and sends results back to Slack
    """
    try:
        form_data = await request.form()

        # Extract command data
        user_id = form_data.get("user_id", "")
        user_name = form_data.get("user_name", "")
        channel_name = form_data.get("channel_name", "")
        text = form_data.get("text", "")
        response_url = form_data.get("response_url", "")

        logger.info(f"TODO command from {user_name}: {text}")

        # Immediate response to Slack (within 3 seconds)
        immediate_response = {
            "response_type": "ephemeral",
            "text": "🔄 TODOワークフローを開始しています...",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*📋 TODOワークフロー開始*\n\n入力内容: `{text}`"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"実行者: <@{user_id}> | 処理中..."
                        }
                    ]
                }
            ]
        }

        # Schedule background task for workflow execution
        if text:
            background_tasks.add_task(
                execute_todo_workflow_and_respond,
                text=text,
                user_name=user_name,
                user_id=user_id,
                response_url=response_url
            )
        else:
            immediate_response = {
                "response_type": "ephemeral",
                "text": "❌ TODOの内容を入力してください",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*使い方:*\n`/todo 1. タスク1 2. タスク2 3. タスク3`"
                        }
                    }
                ]
            }

        return immediate_response

    except Exception as e:
        logger.error(f"Error in TODO command handler: {e}")
        return {
            "response_type": "ephemeral",
            "text": f"❌ エラー: {str(e)}"
        }


async def execute_todo_workflow_and_respond(
    text: str,
    user_name: str,
    user_id: str,
    response_url: str
):
    """Execute TODO workflow and send results to Slack"""
    try:
        from src.workflows.todo_workflow import run_todo_workflow

        logger.info(f"Executing TODO workflow for {user_name}")

        # Run workflow
        result = await run_todo_workflow(
            email_content=text,
            sender=f"{user_name}@slack.local",
            subject=f"Slack TODO from {user_name}"
        )

        # Format result for Slack
        todo_count = result.get("todo_count", 0)
        todos = result.get("todos", [])
        advised_todos = result.get("advised_todos", [])

        if todo_count > 0:
            # Build success message
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ *TODOワークフロー完了*\n\n{todo_count}件のタスクを処理しました"
                    }
                }
            ]

            # Add each TODO with advice
            for item in advised_todos[:5]:  # Limit to 5 for display
                todo = item.get("todo", {})
                advice = item.get("advice", "")
                index = item.get("index", 0)

                title = todo.get("title", "")
                priority = todo.get("priority", "medium")
                estimated_time = todo.get("estimated_time", "30")

                priority_emoji = {
                    "high": "🔴",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(priority.lower(), "⚪")

                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{priority_emoji} *タスク {index + 1}: {title}*\n優先度: {priority} | 予想時間: {estimated_time}分\n\n💡 *アドバイス:*\n{advice}"
                    }
                })

                blocks.append({"type": "divider"})

            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"実行者: <@{user_id}> | 処理完了 ✓"
                    }
                ]
            })

            delayed_message = {
                "response_type": "in_channel",  # Visible to everyone
                "text": f"✅ {todo_count}件のTODOを処理しました",
                "blocks": blocks
            }
        else:
            delayed_message = {
                "response_type": "ephemeral",
                "text": "⚠️ TODOが見つかりませんでした"
            }

        # Send delayed response
        await send_delayed_response(response_url, delayed_message)

    except Exception as e:
        logger.error(f"Error executing TODO workflow: {e}")

        error_message = {
            "response_type": "ephemeral",
            "text": f"❌ ワークフロー実行エラー: {str(e)}"
        }

        await send_delayed_response(response_url, error_message)


@router.post("/help")
async def handle_help_command(request: Request):
    """Handle /help or similar commands"""
    try:
        form_data = await request.form()
        command = form_data.get("command", "/help")

        return {
            "response_type": "ephemeral",
            "text": "📚 ヘルプ",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*🤖 利用可能なコマンド*"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*`/todo <タスク内容>`*\nTODOワークフローを実行します\n例: `/todo 1. 資料作成 2. 会議準備`"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*@メンション*\nチャンネルでボットにメンションすると応答します\n例: `@bot TODO: タスク内容`"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "その他の質問は管理者までお問い合わせください"
                        }
                    ]
                }
            ]
        }

    except Exception as e:
        logger.error(f"Error in help command: {e}")
        return {
            "response_type": "ephemeral",
            "text": f"❌ エラー: {str(e)}"
        }


@router.post("/debug")
async def handle_debug_command(request: Request):
    """Debug command - shows all received data (for testing)"""
    try:
        form_data = await request.form()

        # Extract all data
        data_dict = {}
        for key in form_data.keys():
            data_dict[key] = form_data.get(key, "")

        # Mask token
        if "token" in data_dict:
            token = data_dict["token"]
            data_dict["token"] = token[:10] + "..." if len(token) > 10 else "***"

        # Format for display
        formatted = "```\n"
        for key, value in data_dict.items():
            formatted += f"{key}: {value}\n"
        formatted += "```"

        return {
            "response_type": "ephemeral",
            "text": "🔍 デバッグ情報",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*受信データ:*\n" + formatted
                    }
                }
            ]
        }

    except Exception as e:
        logger.error(f"Error in debug command: {e}")
        return {
            "response_type": "ephemeral",
            "text": f"❌ エラー: {str(e)}"
        }
