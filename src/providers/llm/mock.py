"""Mock LLM Provider - テスト用モックプロバイダー"""

from typing import Optional, Type, Dict, Any, List
from pydantic import BaseModel
import logging

from src.core.providers.llm import LLMProvider

logger = logging.getLogger(__name__)


class MockLLMProvider(LLMProvider):
    """テスト用モックLLMプロバイダー
    
    実際のAPIを呼び出さずに、事前に定義された応答を返します。
    単体テストやインテグレーションテストで使用します。
    
    Attributes:
        responses: プロンプトと応答のマッピング
        call_history: メソッド呼び出し履歴
    
    Example:
        >>> mock = MockLLMProvider(responses={
        ...     "Hello": "Hi there!",
        ...     "What is AI?": "AI is artificial intelligence."
        ... })
        >>> response = await mock.generate("Hello")
        >>> assert response == "Hi there!"
        >>> assert len(mock.call_history) == 1
    """
    
    def __init__(
        self,
        responses: Optional[Dict[str, str]] = None,
        default_response: str = "Mock response"
    ):
        """
        Args:
            responses: プロンプトと応答のマッピング
            default_response: マッピングにない場合のデフォルト応答
        """
        self.responses = responses or {}
        self.default_response = default_response
        self.call_history: List[Dict[str, Any]] = []
        
        logger.info("MockLLMProvider initialized")
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """モックテキスト生成"""
        # 呼び出し履歴を記録
        self.call_history.append({
            "method": "generate",
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "kwargs": kwargs
        })
        
        # 完全一致で応答を返す
        if prompt in self.responses:
            logger.debug(f"Mock returning predefined response for: {prompt[:50]}")
            return self.responses[prompt]
        
        # デフォルトのモック応答
        logger.debug(f"Mock returning default response for: {prompt[:50]}")
        return f"{self.default_response}: {prompt[:50]}..."
    
    async def generate_json(
        self,
        prompt: str,
        schema: Type[BaseModel],
        temperature: float = 0.7,
        **kwargs
    ) -> BaseModel:
        """モックJSON生成"""
        # 呼び出し履歴を記録
        self.call_history.append({
            "method": "generate_json",
            "prompt": prompt,
            "schema": schema.__name__,
            "temperature": temperature,
            "kwargs": kwargs
        })
        
        # プロンプトに対する応答が定義されていれば、それをパース
        if prompt in self.responses:
            response_text = self.responses[prompt]
            try:
                return schema.parse_raw(response_text)
            except Exception as e:
                logger.warning(f"Failed to parse predefined response as JSON: {e}")
        
        # デフォルトのモックデータを生成
        # 基本的なフィールドだけを持つオブジェクトを返す
        mock_data = {}
        
        # スキーマのフィールドに基づいてモックデータを生成
        for field_name, field_info in schema.model_fields.items():
            # Pydantic v2では field_info.is_required() を使用
            is_required = field_info.is_required()
            
            if is_required:
                # 必須フィールドにデフォルト値を設定
                annotation = field_info.annotation
                
                if annotation == str or (hasattr(annotation, '__origin__') and annotation.__origin__ == str):
                    mock_data[field_name] = f"mock_{field_name}"
                elif annotation == int or (hasattr(annotation, '__origin__') and annotation.__origin__ == int):
                    mock_data[field_name] = 0
                elif annotation == float or (hasattr(annotation, '__origin__') and annotation.__origin__ == float):
                    mock_data[field_name] = 0.0
                elif annotation == bool or (hasattr(annotation, '__origin__') and annotation.__origin__ == bool):
                    mock_data[field_name] = True
                elif annotation == list or (hasattr(annotation, '__origin__') and annotation.__origin__ == list):
                    mock_data[field_name] = []
                else:
                    # その他の型はデフォルトで文字列
                    mock_data[field_name] = f"mock_{field_name}"
        
        logger.debug(f"Mock returning generated JSON for schema: {schema.__name__}")
        return schema.model_validate(mock_data)
    
    async def generate_with_context(
        self,
        user_query: str,
        context: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """モックコンテキスト付き生成"""
        # 呼び出し履歴を記録
        self.call_history.append({
            "method": "generate_with_context",
            "user_query": user_query,
            "context": context[:100],  # コンテキストは最初の100文字だけ記録
            "system_instruction": system_instruction,
            "temperature": temperature,
            "kwargs": kwargs
        })
        
        # クエリに対する応答が定義されていれば返す
        if user_query in self.responses:
            logger.debug(f"Mock returning predefined response for query: {user_query[:50]}")
            return self.responses[user_query]
        
        # デフォルトのモック応答
        logger.debug(f"Mock returning default response for query: {user_query[:50]}")
        return f"Mock answer for: {user_query}"
    
    def reset_history(self):
        """呼び出し履歴をクリア"""
        self.call_history = []
        logger.debug("Mock call history reset")
    
    def get_call_count(self, method: Optional[str] = None) -> int:
        """特定のメソッドの呼び出し回数を取得
        
        Args:
            method: メソッド名（Noneの場合は全メソッド）
        
        Returns:
            呼び出し回数
        """
        if method is None:
            return len(self.call_history)
        
        return sum(1 for call in self.call_history if call["method"] == method)

