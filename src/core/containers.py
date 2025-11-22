"""Dependency Injection Container

このモジュールは、dependency-injectorを使用した依存性注入コンテナを提供します。
全てのプロバイダー、サービス、ノード、ワークフローの依存性を一元管理します。

Example:
    >>> from src.core.containers import Container
    >>> container = Container()
    >>> container.config.from_dict({
    ...     'gemini': {
    ...         'api_key': 'your-api-key',
    ...         'model': 'gemini-2.0-flash-exp'
    ...     }
    ... })
    >>> 
    >>> # LLMプロバイダーを取得
    >>> llm_provider = container.llm_provider()
    >>> 
    >>> # ワークフローを取得（依存性は自動注入）
    >>> chat_workflow = container.chat_workflow()
"""

from dependency_injector import containers, providers
from typing import Optional

from src.core.config import settings
from src.core.providers.llm import LLMProvider
from src.core.providers.rag import RAGProvider
from src.providers.llm.gemini import GeminiProvider
from src.providers.llm.mock import MockLLMProvider
from src.providers.rag.simple import SimpleRAGProvider


class Container(containers.DeclarativeContainer):
    """依存性注入コンテナ
    
    全てのプロバイダー、サービス、ノード、ワークフローの依存性を管理します。
    
    Attributes:
        config: 設定プロバイダー
        llm_provider: LLMプロバイダー
        rag_provider: RAGプロバイダー
        chat_workflow: チャットワークフロー
        rag_workflow: RAGワークフロー
    
    Example:
        >>> container = Container()
        >>> # 設定を注入
        >>> container.config.from_dict({
        ...     'llm_provider_type': 'gemini',
        ...     'gemini': {'api_key': 'xxx'}
        ... })
        >>> # プロバイダーを取得
        >>> provider = container.llm_provider()
    """
    
    # 設定管理
    config = providers.Configuration()
    
    # ============================================================================
    # Core Settings
    # ============================================================================
    
    # Settingsインスタンス（シングルトン）
    settings_instance = providers.Singleton(
        lambda: settings
    )
    
    # ============================================================================
    # Provider Layer
    # ============================================================================
    
    # LLM Providers
    gemini_provider = providers.Singleton(
        GeminiProvider,
        api_key=config.gemini.api_key.as_(str, default=lambda: settings.gemini_api_key),
        model=config.gemini.model.as_(str, default="gemini-2.0-flash-exp")
    )
    
    mock_llm_provider = providers.Singleton(
        MockLLMProvider,
        responses=config.mock.responses.as_(dict, default={})
    )
    
    # LLMプロバイダーファクトリー（動的切り替え）
    llm_provider = providers.Selector(
        config.llm_provider_type.as_(str, default="gemini"),
        gemini=gemini_provider,
        mock=mock_llm_provider
    )
    
    # RAG Providers
    simple_rag_provider = providers.Singleton(
        SimpleRAGProvider
    )
    
    # RAGプロバイダーファクトリー（動的切り替え）
    rag_provider = providers.Selector(
        config.rag_provider_type.as_(str, default="simple"),
        simple=simple_rag_provider
    )
    
    # ============================================================================
    # Node Layer
    # ============================================================================
    
    # LLMNode
    llm_node = providers.Factory(
        lambda provider, name="llm_node": _create_llm_node(provider, name),
        provider=llm_provider
    )
    
    # TodoAdvisorNode
    todo_advisor_node = providers.Factory(
        lambda provider: _create_todo_advisor_node(provider),
        provider=llm_provider
    )
    
    # TodoParserNode
    todo_parser_node = providers.Factory(
        lambda provider: _create_todo_parser_node(provider),
        provider=llm_provider
    )
    
    # ============================================================================
    # Workflow Layer
    # ============================================================================
    
    # ChatWorkflow
    chat_workflow = providers.Factory(
        lambda provider: _create_chat_workflow(provider),
        provider=llm_provider
    )
    
    # RAGQueryWorkflow
    rag_query_workflow = providers.Factory(
        lambda provider: _create_rag_query_workflow(provider),
        provider=rag_provider
    )
    
    # ============================================================================
    # Service Layer
    # ============================================================================
    
    # RAGService
    rag_service = providers.Factory(
        lambda llm_provider: _create_rag_service(llm_provider),
        llm_provider=llm_provider
    )


# ============================================================================
# Factory Functions (遅延import)
# ============================================================================

def _create_llm_node(provider: LLMProvider, name: str):
    """LLMNodeを作成（循環importを避けるため遅延import）"""
    from src.nodes.primitives.llm.gemini.node import LLMNode
    return LLMNode(provider=provider, name=name)


def _create_todo_advisor_node(provider: LLMProvider):
    """TodoAdvisorNodeを作成"""
    from src.nodes.composites.todo.advisor.node import TodoAdvisorNode
    return TodoAdvisorNode(provider=provider)


def _create_todo_parser_node(provider: LLMProvider):
    """TodoParserNodeを作成"""
    from src.nodes.composites.todo.parser.node import TodoParserNode
    return TodoParserNode(provider=provider)


def _create_chat_workflow(provider: LLMProvider):
    """ChatWorkflowを作成"""
    from src.workflows.atomic.chat import ChatWorkflow
    return ChatWorkflow(llm_provider=provider)


def _create_rag_query_workflow(provider: RAGProvider):
    """RAGQueryWorkflowを作成"""
    from src.workflows.atomic.rag_query import RAGQueryWorkflow
    return RAGQueryWorkflow(rag_provider=provider)


def _create_rag_service(llm_provider: LLMProvider):
    """RAGServiceを作成"""
    from src.services.rag.rag_service import RAGService
    return RAGService(llm_provider=llm_provider)


# ============================================================================
# Global Container Instance
# ============================================================================

# グローバルコンテナインスタンス（シングルトン）
_container: Optional[Container] = None


def get_container() -> Container:
    """グローバルコンテナインスタンスを取得
    
    Returns:
        Container: DIコンテナインスタンス
    
    Example:
        >>> container = get_container()
        >>> provider = container.llm_provider()
    """
    global _container
    if _container is None:
        _container = Container()
        # デフォルト設定を適用
        _container.config.from_dict({
            'llm_provider_type': 'gemini',
            'rag_provider_type': 'simple',
            'gemini': {
                'api_key': settings.gemini_api_key,
                'model': 'gemini-2.0-flash-exp'
            }
        })
    return _container


def reset_container():
    """グローバルコンテナをリセット（テスト用）"""
    global _container
    _container = None


# ============================================================================
# Convenience Functions
# ============================================================================

def get_llm_provider(provider_type: Optional[str] = None) -> LLMProvider:
    """LLMプロバイダーを取得
    
    Args:
        provider_type: プロバイダータイプ（省略時はデフォルト）
    
    Returns:
        LLMProvider: LLMプロバイダーインスタンス
    
    Example:
        >>> provider = get_llm_provider()
        >>> response = await provider.generate("Hello")
    """
    container = get_container()
    if provider_type:
        container.config.llm_provider_type.from_value(provider_type)
    return container.llm_provider()


def get_rag_provider(provider_type: Optional[str] = None) -> RAGProvider:
    """RAGプロバイダーを取得
    
    Args:
        provider_type: プロバイダータイプ（省略時はデフォルト）
    
    Returns:
        RAGProvider: RAGプロバイダーインスタンス
    """
    container = get_container()
    if provider_type:
        container.config.rag_provider_type.from_value(provider_type)
    return container.rag_provider()


def get_chat_workflow():
    """ChatWorkflowを取得（依存性は自動注入）
    
    Returns:
        ChatWorkflow: チャットワークフローインスタンス
    
    Example:
        >>> workflow = get_chat_workflow()
        >>> result = await workflow.run(ChatInput(message="Hello"))
    """
    container = get_container()
    return container.chat_workflow()


def get_rag_query_workflow():
    """RAGQueryWorkflowを取得（依存性は自動注入）
    
    Returns:
        RAGQueryWorkflow: RAGクエリワークフローインスタンス
    """
    container = get_container()
    return container.rag_query_workflow()

