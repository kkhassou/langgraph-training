"""Pytest Configuration and Fixtures

全テストで共有されるフィクスチャと設定を定義します。
"""

import pytest
import asyncio
from typing import Dict, Any, Generator
from fastapi.testclient import TestClient

from src.providers.llm.mock import MockLLMProvider
from src.main import app


@pytest.fixture(scope="session")
def event_loop():
    """イベントループのフィクスチャ（セッションスコープ）"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_llm_provider() -> MockLLMProvider:
    """テスト用のモックLLMプロバイダー"""
    return MockLLMProvider(
        responses={
            "test": "test response",
            "hello": "Hello! How can I help you?",
            "error": "This will cause an error"
        }
    )


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """テスト用のFastAPIクライアント
    
    FastAPIのTestClientを使用してAPIエンドポイントをテストします。
    依存性のオーバーライドが可能です。
    """
    with TestClient(app) as client:
        yield client
    
    # テスト後にクリーンアップ
    app.dependency_overrides.clear()


@pytest.fixture
def mock_dependencies():
    """依存性をモックに置き換えるヘルパー
    
    Example:
        >>> def test_example(test_client, mock_dependencies):
        >>>     from src.api.dependencies import get_llm_provider
        >>>     mock_dependencies(get_llm_provider, MockLLMProvider())
        >>>     response = test_client.post("/workflows/atomic/chat", ...)
    """
    def _override(dependency_callable, mock_obj):
        app.dependency_overrides[dependency_callable] = lambda: mock_obj
    
    return _override


@pytest.fixture
def sample_node_state():
    """サンプルのNodeStateフィクスチャ"""
    from src.nodes.base import NodeState
    
    state = NodeState()
    state.messages = ["test message"]
    state.data = {"test_key": "test_value"}
    state.metadata = {"request_id": "test-123"}
    
    return state


@pytest.fixture
def sample_chat_input():
    """サンプルのChatInputフィクスチャ"""
    from src.workflows.atomic.chat import ChatInput
    
    return ChatInput(
        message="テストメッセージ",
        temperature=0.7,
        max_tokens=1000
    )


# Pytest設定
def pytest_configure(config):
    """Pytest設定のカスタマイズ"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )


def pytest_collection_modifyitems(config, items):
    """テストアイテムのカスタマイズ"""
    # 統合テストにマーカーを自動追加
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "test_e2e" in item.nodeid:
            item.add_marker(pytest.mark.integration)

