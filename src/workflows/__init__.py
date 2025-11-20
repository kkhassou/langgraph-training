"""Workflows - LangGraph workflow implementations organized by category"""
from .basic import (
    SimpleChatGraph,
    SimpleChatInput,
    SimpleChatOutput,
    PPTSummaryGraph,
    PPTSummaryInput,
    PPTSummaryOutput,
    SlackReportGraph,
    SlackReportInput,
    SlackReportOutput,
)
from .rag import (
    RAGWorkflow,
    RAGWorkflowInput,
    RAGWorkflowOutput,
)
from .patterns import (
    ReflectionGraph,
    ReflectionInput,
    ReflectionOutput,
    ChainOfThoughtGraph,
    ChainOfThoughtInput,
    ChainOfThoughtOutput,
)
from .todo import (
    run_todo_workflow,
    create_todo_workflow,
)

__all__ = [
    # Basic workflows
    "SimpleChatGraph",
    "SimpleChatInput",
    "SimpleChatOutput",
    "PPTSummaryGraph",
    "PPTSummaryInput",
    "PPTSummaryOutput",
    "SlackReportGraph",
    "SlackReportInput",
    "SlackReportOutput",
    # RAG workflows
    "RAGWorkflow",
    "RAGWorkflowInput",
    "RAGWorkflowOutput",
    # Pattern workflows
    "ReflectionGraph",
    "ReflectionInput",
    "ReflectionOutput",
    "ChainOfThoughtGraph",
    "ChainOfThoughtInput",
    "ChainOfThoughtOutput",
    # TODO workflows
    "run_todo_workflow",
    "create_todo_workflow",
]

