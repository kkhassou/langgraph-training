"""Basic workflows - Simple chat, document processing, and integrations"""
from .simple_chat import SimpleChatGraph, SimpleChatInput, SimpleChatOutput
from .ppt_summary import PPTSummaryGraph, PPTSummaryInput, PPTSummaryOutput
from .slack_report import SlackReportGraph, SlackReportInput, SlackReportOutput

__all__ = [
    "SimpleChatGraph",
    "SimpleChatInput",
    "SimpleChatOutput",
    "PPTSummaryGraph",
    "PPTSummaryInput",
    "PPTSummaryOutput",
    "SlackReportGraph",
    "SlackReportInput",
    "SlackReportOutput",
]

