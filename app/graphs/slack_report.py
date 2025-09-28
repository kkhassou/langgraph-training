from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from pydantic import BaseModel

from app.nodes.base_node import NodeState
from app.nodes.mcp_integrations.slack_mcp_node import SlackMCPNode, SlackMCPActionType
from app.nodes.llm_gemini import GeminiNode


class SlackReportInput(BaseModel):
    """Input model for Slack report graph"""
    channel_id: str
    days_back: int = 7
    limit: int = 100
    report_type: str = "summary"  # summary, insights, action_items


class SlackReportOutput(BaseModel):
    """Output model for Slack report graph"""
    report: str
    message_count: int = 0
    success: bool = True
    error_message: str = None
    messages: List[Dict[str, Any]] = []


class SlackReportGraph:
    """Slack report generation workflow using LangGraph"""

    def __init__(self):
        self.slack_node = SlackMCPNode()
        self.gemini_node = GeminiNode()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(NodeState)

        # Add nodes
        workflow.add_node("collect_messages", self._collect_messages_step)
        workflow.add_node("generate_report", self._generate_report_step)

        # Set entry point
        workflow.set_entry_point("collect_messages")

        # Add edges
        workflow.add_edge("collect_messages", "generate_report")
        workflow.add_edge("generate_report", END)

        return workflow.compile()

    async def _collect_messages_step(self, state: NodeState) -> NodeState:
        """Collect messages from Slack channel"""
        # Configure Slack node for message collection
        state.data["action"] = SlackMCPActionType.GET_MESSAGES

        return await self.slack_node.execute(state)

    async def _generate_report_step(self, state: NodeState) -> NodeState:
        """Generate report from collected messages"""
        if "error" in state.data:
            return state

        # Get collected messages
        messages = state.data.get("messages", [])
        if not messages:
            state.data["error"] = "No messages found in the specified timeframe"
            return state

        # Format messages for analysis
        messages_text = self._format_messages_for_analysis(messages)
        report_type = state.data.get("report_type", "summary")

        # Create report generation prompt
        report_prompts = {
            "summary": "以下のSlackメッセージを分析し、議論内容、主要トピック、全体的なテーマの包括的な要約を日本語で提供してください：",
            "insights": "以下のSlackメッセージを分析し、主要な洞察、トレンド、重要な観察事項を日本語で抽出してください：",
            "action_items": "以下のSlackメッセージを分析し、アクションアイテム、決定事項、フォローアップタスクを日本語で特定してください："
        }

        prompt = f"""
{report_prompts.get(report_type, report_prompts["summary"])}

チャンネルメッセージ（全{len(messages)}件）：
{messages_text}

これらの会話から最も重要な情報を捉えた、読みやすい構造化されたレポートを日本語で提供してください。
        """.strip()

        # Update state for Gemini node
        state.messages = [prompt]
        state.data["prompt"] = prompt

        return await self.gemini_node.execute(state)

    def _format_messages_for_analysis(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages for LLM analysis"""
        formatted_messages = []

        for msg in messages:
            if msg.get("text", "").strip():
                user = msg.get("user", "Unknown")
                timestamp = msg.get("timestamp", "")
                text = msg.get("text", "")

                # Format timestamp if available
                time_str = ""
                if timestamp:
                    try:
                        from datetime import datetime
                        dt = datetime.fromtimestamp(float(timestamp))
                        time_str = f" [{dt.strftime('%Y-%m-%d %H:%M')}]"
                    except:
                        pass

                formatted_messages.append(f"{user}{time_str}: {text}")

        return "\n\n".join(formatted_messages)

    async def run(self, input_data: SlackReportInput) -> SlackReportOutput:
        """Run the Slack report workflow"""
        try:
            # Initialize state
            initial_state = NodeState()
            initial_state.data = {
                "channel_id": input_data.channel_id,
                "days_back": input_data.days_back,
                "limit": input_data.limit,
                "report_type": input_data.report_type
            }

            # Run the graph
            result = await self.graph.ainvoke(initial_state)

            # Extract results
            if "error" in result["data"]:
                return SlackReportOutput(
                    report="",
                    success=False,
                    error_message=result["data"]["error"]
                )

            report = result["data"].get("llm_response", "No report generated")
            messages = result["data"].get("messages", [])
            message_count = len(messages)

            return SlackReportOutput(
                report=report,
                message_count=message_count,
                messages=messages,
                success=True
            )

        except Exception as e:
            return SlackReportOutput(
                report="",
                success=False,
                error_message=str(e)
            )

    def get_mermaid_diagram(self) -> str:
        """Get Mermaid diagram representation of the graph"""
        return """
graph TD
    A[Start: Channel ID + Timeframe] --> B[Slack Message Collection]
    B --> C{Messages Found?}
    C -->|Yes| D[Format Messages]
    C -->|No| F[Error: No Messages]
    D --> E[Gemini Report Generation]
    E --> G[End: Generated Report]
    F --> G

    classDef startEnd fill:#e1f5fe
    classDef slack fill:#4a154b,color:#ffffff
    classDef processing fill:#fff3e0
    classDef llm fill:#f3e5f5
    classDef decision fill:#e8f5e8
    classDef error fill:#ffebee

    class A,G startEnd
    class B slack
    class D processing
    class E llm
    class C decision
    class F error
        """