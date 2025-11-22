"""Provider層の基本的なテスト"""

import pytest
from pydantic import BaseModel
from typing import List

from src.core.providers.llm import LLMProvider
from src.providers.llm.mock import MockLLMProvider


class TestMockLLMProvider:
    """MockLLMProviderのテスト"""
    
    @pytest.mark.asyncio
    async def test_generate_with_predefined_response(self):
        """事前定義された応答を返すテスト"""
        mock = MockLLMProvider(responses={
            "Hello": "Hi there!",
            "What is AI?": "AI is artificial intelligence."
        })
        
        # テスト実行
        response = await mock.generate("Hello")
        
        # 検証
        assert response == "Hi there!"
        assert len(mock.call_history) == 1
        assert mock.call_history[0]["method"] == "generate"
        assert mock.call_history[0]["prompt"] == "Hello"
    
    @pytest.mark.asyncio
    async def test_generate_with_default_response(self):
        """デフォルト応答を返すテスト"""
        mock = MockLLMProvider(default_response="Default mock")
        
        response = await mock.generate("Unknown prompt")
        
        assert "Default mock" in response
        assert len(mock.call_history) == 1
    
    @pytest.mark.asyncio
    async def test_generate_with_temperature(self):
        """温度パラメータが記録されることをテスト"""
        mock = MockLLMProvider()
        
        await mock.generate("Test", temperature=0.9, max_tokens=500)
        
        call = mock.call_history[0]
        assert call["temperature"] == 0.9
        assert call["max_tokens"] == 500
    
    @pytest.mark.asyncio
    async def test_generate_json(self):
        """JSON生成のテスト"""
        class TestSchema(BaseModel):
            title: str
            count: int
        
        mock = MockLLMProvider()
        result = await mock.generate_json("Generate test data", schema=TestSchema)
        
        # 結果がスキーマに準拠していることを確認
        assert isinstance(result, TestSchema)
        assert hasattr(result, "title")
        assert hasattr(result, "count")
        
        # 呼び出し履歴を確認
        assert len(mock.call_history) == 1
        assert mock.call_history[0]["method"] == "generate_json"
        assert mock.call_history[0]["schema"] == "TestSchema"
    
    @pytest.mark.asyncio
    async def test_generate_with_context(self):
        """コンテキスト付き生成のテスト"""
        mock = MockLLMProvider(responses={
            "What is ML?": "Machine Learning is a subset of AI."
        })
        
        response = await mock.generate_with_context(
            user_query="What is ML?",
            context="ML is used in many applications...",
            system_instruction="Answer as an expert"
        )
        
        assert response == "Machine Learning is a subset of AI."
        
        call = mock.call_history[0]
        assert call["method"] == "generate_with_context"
        assert call["user_query"] == "What is ML?"
        assert call["system_instruction"] == "Answer as an expert"
    
    def test_reset_history(self):
        """履歴リセットのテスト"""
        mock = MockLLMProvider()
        mock.call_history.append({"test": "data"})
        
        assert len(mock.call_history) == 1
        
        mock.reset_history()
        
        assert len(mock.call_history) == 0
    
    def test_get_call_count(self):
        """呼び出し回数取得のテスト"""
        mock = MockLLMProvider()
        mock.call_history = [
            {"method": "generate"},
            {"method": "generate"},
            {"method": "generate_json"},
        ]
        
        assert mock.get_call_count() == 3
        assert mock.get_call_count("generate") == 2
        assert mock.get_call_count("generate_json") == 1
        assert mock.get_call_count("unknown") == 0


class TestLLMProviderInterface:
    """LLMProviderインターフェースのテスト"""
    
    def test_is_abstract(self):
        """LLMProviderが抽象クラスであることを確認"""
        with pytest.raises(TypeError):
            # 抽象メソッドを実装せずにインスタンス化しようとするとエラー
            LLMProvider()
    
    def test_mock_implements_interface(self):
        """MockLLMProviderがインターフェースを実装していることを確認"""
        mock = MockLLMProvider()
        assert isinstance(mock, LLMProvider)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



