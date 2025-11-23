"""
FastAPI Dependencies - 依存性注入

FastAPIのDepends機能を使用した依存性注入を提供します。
これにより、テスト容易性と依存関係の明示化を実現します。

Example:
    >>> from fastapi import Depends
    >>> from src.api.dependencies import get_chat_workflow
    >>> 
    >>> @router.post("/chat")
    >>> async def chat(
    >>>     input_data: ChatInput,
    >>>     workflow: ChatWorkflow = Depends(get_chat_workflow)
    >>> ):
    >>>     return await workflow.run(input_data)
"""

from typing import Optional
from functools import lru_cache

from src.core.config import settings
from src.core.providers.llm import LLMProvider
from src.core.providers.rag import RAGProvider
from src.providers.llm.gemini import GeminiProvider
from src.providers.llm.mock import MockLLMProvider
from src.providers.rag.simple import SimpleRAGProvider


# ============================================================================
# Provider Dependencies
# ============================================================================

@lru_cache()
def get_llm_provider(provider_type: Optional[str] = None) -> LLMProvider:
    """LLMプロバイダーを取得
    
    シングルトンとして動作し、同じプロバイダーインスタンスを返します。
    
    Args:
        provider_type: プロバイダータイプ（省略時は設定から取得）
    
    Returns:
        LLMProvider: LLMプロバイダーインスタンス
    
    Example:
        >>> from fastapi import Depends
        >>> 
        >>> @router.post("/generate")
        >>> async def generate(
        >>>     prompt: str,
        >>>     provider: LLMProvider = Depends(get_llm_provider)
        >>> ):
        >>>     return await provider.generate(prompt)
    """
    # デフォルトはGemini
    if provider_type is None:
        provider_type = "gemini"
    
    if provider_type == "gemini":
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model="gemini-2.0-flash-exp"
        )
    elif provider_type == "mock":
        return MockLLMProvider(responses={})
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")


def get_gemini_provider() -> GeminiProvider:
    """Geminiプロバイダーを取得
    
    Returns:
        GeminiProvider: Geminiプロバイダーインスタンス
    """
    return GeminiProvider(
        api_key=settings.gemini_api_key,
        model="gemini-2.0-flash-exp"
    )


def get_mock_llm_provider() -> MockLLMProvider:
    """モックLLMプロバイダーを取得（テスト用）
    
    Returns:
        MockLLMProvider: モックLLMプロバイダーインスタンス
    """
    return MockLLMProvider(responses={})


@lru_cache()
def get_rag_provider() -> RAGProvider:
    """RAGプロバイダーを取得
    
    Returns:
        RAGProvider: RAGプロバイダーインスタンス
    """
    return SimpleRAGProvider()


# ============================================================================
# Workflow Dependencies
# ============================================================================

def get_chat_workflow(provider: LLMProvider = None):
    """ChatWorkflowを取得
    
    Args:
        provider: LLMプロバイダー（省略時はデフォルトプロバイダーを使用）
    
    Returns:
        ChatWorkflow: チャットワークフローインスタンス
    
    Example:
        >>> @router.post("/chat")
        >>> async def chat(
        >>>     input_data: ChatInput,
        >>>     workflow: ChatWorkflow = Depends(get_chat_workflow)
        >>> ):
        >>>     return await workflow.run(input_data)
    """
    from src.workflows.atomic.chat import ChatWorkflow
    
    if provider is None:
        provider = get_llm_provider()
    
    return ChatWorkflow(llm_provider=provider)


def get_rag_query_workflow(rag_provider: RAGProvider = None):
    """RAGQueryWorkflowを取得
    
    Args:
        rag_provider: RAGプロバイダー（省略時はデフォルトプロバイダーを使用）
    
    Returns:
        RAGQueryWorkflow: RAGクエリワークフローインスタンス
    """
    from src.workflows.atomic.rag_query import RAGQueryWorkflow
    
    if rag_provider is None:
        rag_provider = get_rag_provider()
    
    return RAGQueryWorkflow(rag_provider=rag_provider)


def get_document_extract_workflow():
    """DocumentExtractWorkflowを取得
    
    Returns:
        DocumentExtractWorkflow: ドキュメント抽出ワークフローインスタンス
    """
    from src.workflows.atomic.document_extract import DocumentExtractWorkflow
    return DocumentExtractWorkflow()


def get_ppt_summary_workflow(provider: LLMProvider = None):
    """PPTSummaryWorkflowを取得
    
    Args:
        provider: LLMプロバイダー（省略時はデフォルトプロバイダーを使用）
    
    Returns:
        PPTSummaryWorkflow: PPT要約ワークフローインスタンス
    """
    from src.workflows.composite.document_analysis.ppt_summary import PPTSummaryWorkflow
    
    if provider is None:
        provider = get_llm_provider()
    
    return PPTSummaryWorkflow(llm_provider=provider)


def get_chain_of_thought_workflow(provider: LLMProvider = None):
    """ChainOfThoughtWorkflowを取得
    
    Args:
        provider: LLMプロバイダー（省略時はデフォルトプロバイダーを使用）
    
    Returns:
        ChainOfThoughtWorkflow: Chain of Thoughtワークフローインスタンス
    """
    from src.workflows.composite.intelligent_chat.chain_of_thought import ChainOfThoughtWorkflow
    
    if provider is None:
        provider = get_llm_provider()
    
    return ChainOfThoughtWorkflow(llm_provider=provider)


def get_reflection_workflow(provider: LLMProvider = None):
    """ReflectionWorkflowを取得
    
    Args:
        provider: LLMプロバイダー（省略時はデフォルトプロバイダーを使用）
    
    Returns:
        ReflectionWorkflow: Reflectionワークフローインスタンス
    """
    from src.workflows.composite.intelligent_chat.reflection import ReflectionWorkflow
    
    if provider is None:
        provider = get_llm_provider()
    
    return ReflectionWorkflow(llm_provider=provider)


# ============================================================================
# Service Dependencies
# ============================================================================

def get_rag_service(llm_provider: LLMProvider = None):
    """RAGServiceを取得
    
    Args:
        llm_provider: LLMプロバイダー（省略時はデフォルトプロバイダーを使用）
    
    Returns:
        RAGService: RAGサービスインスタンス
    """
    from src.services.rag.rag_service import RAGService
    
    if llm_provider is None:
        llm_provider = get_llm_provider()
    
    return RAGService(llm_provider=llm_provider)


def get_document_service():
    """DocumentServiceを取得
    
    Returns:
        DocumentService: ドキュメントサービスインスタンス
    """
    from src.services.document.document_service import DocumentService
    return DocumentService()


# ============================================================================
# MCP Service Dependencies
# ============================================================================

def get_slack_service():
    """SlackServiceを取得
    
    Returns:
        SlackService: Slackサービスインスタンス
    """
    from src.services.mcp.slack import SlackService
    return SlackService()


def get_github_service():
    """GitHubServiceを取得
    
    Returns:
        GitHubService: GitHubサービスインスタンス
    """
    from src.services.mcp.github import GitHubService
    return GitHubService()


def get_notion_service():
    """NotionServiceを取得
    
    Returns:
        NotionService: Notionサービスインスタンス
    """
    from src.services.mcp.notion import NotionService
    return NotionService()


# ============================================================================
# Node Dependencies
# ============================================================================

def get_llm_node(provider: LLMProvider = None):
    """LLMNodeを取得
    
    Args:
        provider: LLMプロバイダー（省略時はデフォルトプロバイダーを使用）
    
    Returns:
        LLMNode: LLMノードインスタンス
    """
    from src.nodes.blocks.llm import LLMNode
    
    if provider is None:
        provider = get_llm_provider()
    
    return LLMNode(provider=provider, name="llm_node")


def get_retrieval_node():
    """RetrievalNodeを取得
    
    Returns:
        RetrievalNode: 検索ノードインスタンス
    """
    from src.nodes.blocks.retrieval import RetrievalNode
    return RetrievalNode(name="retrieval_node")

