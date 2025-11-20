from fastapi import APIRouter, HTTPException, UploadFile, File
import tempfile
import os

from src.workflows.basic import SimpleChatGraph, SimpleChatInput
from src.workflows.basic import PPTSummaryGraph, PPTSummaryInput
# Temporarily disabled due to MCP dependency issue
# from src.workflows.basic import SlackReportGraph, SlackReportInput
from src.workflows.rag import RAGWorkflow, RAGWorkflowInput
from src.workflows.patterns import ReflectionGraph, ReflectionInput
from src.workflows.patterns import ChainOfThoughtGraph, ChainOfThoughtInput

router = APIRouter(prefix="/graphs", tags=["graphs"])

# Initialize graph instances
simple_chat_graph = SimpleChatGraph()
ppt_summary_graph = PPTSummaryGraph()
# slack_report_graph = SlackReportGraph()  # Temporarily disabled
rag_workflow = RAGWorkflow()
reflection_graph = ReflectionGraph()
chain_of_thought_graph = ChainOfThoughtGraph()


@router.post("/simple-chat")
async def run_simple_chat(input_data: SimpleChatInput):
    """Run simple chat workflow"""
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


# @router.post("/slack-report")
# async def run_slack_report(input_data: SlackReportInput):
#     """Run Slack report generation workflow"""
#     try:
#         result = await slack_report_graph.run(input_data)
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@router.post("/reflection")
async def run_reflection(input_data: ReflectionInput):
    """Run reflection pattern workflow"""
    try:
        result = await reflection_graph.run(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chain-of-thought")
async def run_chain_of_thought(input_data: ChainOfThoughtInput):
    """Run Chain of Thought pattern workflow"""
    try:
        result = await chain_of_thought_graph.run(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag-workflow")
async def run_rag_workflow(input_data: RAGWorkflowInput):
    """Run RAG workflow with multiple strategies"""
    try:
        result = await rag_workflow.run(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diagrams/{graph_name}")
async def get_graph_diagram(graph_name: str):
    """Get Mermaid diagram for a specific graph"""
    try:
        diagrams = {
            "simple-chat": simple_chat_graph.get_mermaid_diagram(),
            "ppt-summary": ppt_summary_graph.get_mermaid_diagram(),
            # "slack-report": slack_report_graph.get_mermaid_diagram(),  # Temporarily disabled
            "rag-workflow": rag_workflow.get_mermaid_diagram(),
            "reflection": reflection_graph.get_mermaid_diagram(),
            "chain-of-thought": chain_of_thought_graph.get_mermaid_diagram()
        }

        if graph_name not in diagrams:
            raise HTTPException(status_code=404, detail=f"Graph '{graph_name}' not found")

        return {
            "graph_name": graph_name,
            "mermaid_diagram": diagrams[graph_name]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_graphs():
    """List available graph workflows"""
    return {
        "available_graphs": [
            {
                "name": "simple-chat",
                "endpoint": "/graphs/simple-chat",
                "description": "Simple chat workflow using Gemini LLM",
                "method": "POST"
            },
            {
                "name": "ppt-summary",
                "endpoint": "/graphs/ppt-summary",
                "description": "PowerPoint summarization workflow",
                "method": "POST"
            },
            # {
            #     "name": "slack-report",
            #     "endpoint": "/graphs/slack-report",
            #     "description": "Slack message analysis and reporting workflow",
            #     "method": "POST"
            # },
            {
                "name": "rag-workflow",
                "endpoint": "/graphs/rag-workflow",
                "description": "Advanced RAG workflow with multiple strategies",
                "method": "POST"
            },
            {
                "name": "reflection",
                "endpoint": "/graphs/reflection",
                "description": "Reflection pattern for iterative improvement",
                "method": "POST"
            },
            {
                "name": "chain-of-thought",
                "endpoint": "/graphs/chain-of-thought",
                "description": "Chain of Thought reasoning pattern",
                "method": "POST"
            }
        ]
    }