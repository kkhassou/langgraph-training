"""Pytest Configuration and Fixtures

全テストで共有されるフィクスチャと設定を定義します。
"""

import pytest
import asyncio
from typing import Dict, Any, Generator

from src.providers.llm.mock import MockLLMProvider
from src.core.containers import Container, reset_container


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
def test_container() -> Generator[Container, None, None]:
    """テスト用のDIコンテナ
    
    テスト前にリセットし、テスト後もクリーンアップします。
    """
    # テスト前にコンテナをリセット
    reset_container()
    
    # 新しいコンテナを作成
    container = Container()
    container.config.from_dict({
        'llm_provider_type': 'mock',
        'rag_provider_type': 'simple',
        'mock': {
            'responses': {
                'test': 'test response'
            }
        }
    })
    
    yield container
    
    # テスト後にクリーンアップ
    reset_container()


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

