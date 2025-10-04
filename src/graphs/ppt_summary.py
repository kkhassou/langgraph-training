from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from pydantic import BaseModel

from src.nodes.base import NodeState
from src.nodes.document.ppt_ingest import PowerPointIngestNode
from src.nodes.llm.gemini import GeminiNode


class PPTSummaryInput(BaseModel):
    """Input model for PowerPoint summary graph"""
    file_path: str
    summary_style: str = "bullet_points"  # bullet_points, paragraph, key_insights


class PPTSummaryOutput(BaseModel):
    """Output model for PowerPoint summary graph"""
    summary: str
    slide_count: int = 0
    success: bool = True
    error_message: str = None
    extracted_slides: List[Dict[str, Any]] = []


class PPTSummaryGraph:
    """PowerPoint summary workflow using LangGraph"""

    def __init__(self):
        self.ppt_ingest_node = PowerPointIngestNode()
        self.gemini_node = GeminiNode()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(NodeState)

        # Add nodes
        workflow.add_node("ppt_ingest", self._ppt_ingest_step)
        workflow.add_node("summarize", self._summarize_step)

        # Set entry point
        workflow.set_entry_point("ppt_ingest")

        # Add edges
        workflow.add_edge("ppt_ingest", "summarize")
        workflow.add_edge("summarize", END)

        return workflow.compile()

    async def _ppt_ingest_step(self, state: NodeState) -> NodeState:
        """Execute PowerPoint ingestion step"""
        return await self.ppt_ingest_node.execute(state)

    async def _summarize_step(self, state: NodeState) -> NodeState:
        """Execute summarization step"""
        if "error" in state.data:
            return state

        # Get extracted text and format for summarization
        extracted_text = state.data.get("extracted_text", [])
        if not extracted_text:
            state.data["error"] = "No text extracted from PowerPoint"
            return state

        # Format content for LLM
        content_text = self._format_slides_for_summary(extracted_text)
        summary_style = state.data.get("summary_style", "bullet_points")

        # Create summarization prompt
        style_prompts = {
            "bullet_points": "以下のPowerPointプレゼンテーションを分かりやすい箇条書きで要約してください：",
            "paragraph": "以下のPowerPointプレゼンテーションを一貫した段落で要約してください：",
            "key_insights": "以下のPowerPointプレゼンテーションから重要な洞察と主要なポイントを抽出してください："
        }

        prompt = f"""
{style_prompts.get(summary_style, style_prompts["bullet_points"])}

{content_text}

プレゼンテーションの主要なポイントと重要な情報を捉えた、明確で簡潔な要約を日本語で提供してください。
        """.strip()

        # Update state for Gemini node
        state.messages = [prompt]
        state.data["prompt"] = prompt

        return await self.gemini_node.execute(state)

    def _format_slides_for_summary(self, slides: List[Dict[str, Any]]) -> str:
        """Format slide content for summarization"""
        formatted_content = []

        for slide in slides:
            slide_text = f"Slide {slide['slide_number']}:"

            if slide.get("title"):
                slide_text += f"\nTitle: {slide['title']}"

            if slide.get("content"):
                slide_text += "\nContent:"
                for content in slide["content"]:
                    slide_text += f"\n- {content}"

            if slide.get("notes"):
                slide_text += f"\nNotes: {slide['notes']}"

            formatted_content.append(slide_text)

        return "\n\n".join(formatted_content)

    async def run(self, input_data: PPTSummaryInput) -> PPTSummaryOutput:
        """Run the PowerPoint summary workflow"""
        try:
            # Initialize state
            initial_state = NodeState()
            initial_state.data = {
                "file_path": input_data.file_path,
                "summary_style": input_data.summary_style
            }

            # Run the graph
            result = await self.graph.ainvoke(initial_state)

            # Extract results
            if "error" in result["data"]:
                return PPTSummaryOutput(
                    summary="",
                    success=False,
                    error_message=result["data"]["error"]
                )

            summary = result["data"].get("llm_response", "No summary generated")
            slide_count = result["data"].get("slide_count", 0)
            extracted_slides = result["data"].get("extracted_text", [])

            return PPTSummaryOutput(
                summary=summary,
                slide_count=slide_count,
                extracted_slides=extracted_slides,
                success=True
            )

        except Exception as e:
            return PPTSummaryOutput(
                summary="",
                success=False,
                error_message=str(e)
            )

    def get_mermaid_diagram(self) -> str:
        """Get Mermaid diagram representation of the graph"""
        return """
graph TD
    A[Start: PowerPoint File] --> B[PPT Ingest Node]
    B --> C{Content Extracted?}
    C -->|Yes| D[Format for Summary]
    C -->|No| F[Error: No Content]
    D --> E[Gemini Summary Node]
    E --> G[End: Generated Summary]
    F --> G

    classDef startEnd fill:#e1f5fe
    classDef processing fill:#fff3e0
    classDef llm fill:#f3e5f5
    classDef decision fill:#e8f5e8
    classDef error fill:#ffebee

    class A,G startEnd
    class B,D processing
    class E llm
    class C decision
    class F error
        """