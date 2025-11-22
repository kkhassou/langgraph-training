"""Provider層の手動テスト（pytest不要）"""

import asyncio
from pydantic import BaseModel

from src.core.providers.llm import LLMProvider
from src.providers.llm.mock import MockLLMProvider


async def test_mock_llm_provider():
    """MockLLMProviderの基本動作テスト"""
    print("🧪 Testing MockLLMProvider...")
    
    # Test 1: 事前定義された応答
    print("\n1. Testing predefined responses...")
    mock = MockLLMProvider(responses={
        "Hello": "Hi there!",
        "What is AI?": "AI is artificial intelligence."
    })
    
    response = await mock.generate("Hello")
    assert response == "Hi there!", f"Expected 'Hi there!', got '{response}'"
    assert len(mock.call_history) == 1
    print("   ✅ Predefined response works")
    
    # Test 2: デフォルト応答
    print("\n2. Testing default response...")
    mock2 = MockLLMProvider(default_response="Default mock")
    response2 = await mock2.generate("Unknown prompt")
    assert "Default mock" in response2
    print("   ✅ Default response works")
    
    # Test 3: パラメータの記録
    print("\n3. Testing parameter recording...")
    mock3 = MockLLMProvider()
    await mock3.generate("Test", temperature=0.9, max_tokens=500)
    call = mock3.call_history[0]
    assert call["temperature"] == 0.9
    assert call["max_tokens"] == 500
    print("   ✅ Parameters recorded correctly")
    
    # Test 4: JSON生成
    print("\n4. Testing JSON generation...")
    class TestSchema(BaseModel):
        title: str
        count: int
    
    mock4 = MockLLMProvider()
    result = await mock4.generate_json("Generate test data", schema=TestSchema)
    assert isinstance(result, TestSchema)
    assert hasattr(result, "title")
    assert hasattr(result, "count")
    print("   ✅ JSON generation works")
    
    # Test 5: コンテキスト付き生成
    print("\n5. Testing context-aware generation...")
    mock5 = MockLLMProvider(responses={
        "What is ML?": "Machine Learning is a subset of AI."
    })
    response5 = await mock5.generate_with_context(
        user_query="What is ML?",
        context="ML is used in many applications...",
        system_instruction="Answer as an expert"
    )
    assert response5 == "Machine Learning is a subset of AI."
    print("   ✅ Context-aware generation works")
    
    # Test 6: 履歴リセット
    print("\n6. Testing history reset...")
    mock6 = MockLLMProvider()
    await mock6.generate("test")
    assert len(mock6.call_history) == 1
    mock6.reset_history()
    assert len(mock6.call_history) == 0
    print("   ✅ History reset works")
    
    # Test 7: 呼び出し回数
    print("\n7. Testing call count...")
    mock7 = MockLLMProvider()
    await mock7.generate("test1")
    await mock7.generate("test2")
    await mock7.generate_json("test3", schema=TestSchema)
    assert mock7.get_call_count() == 3
    assert mock7.get_call_count("generate") == 2
    assert mock7.get_call_count("generate_json") == 1
    print("   ✅ Call count works")
    
    print("\n✅ All MockLLMProvider tests passed!")


async def test_interface():
    """インターフェースのテスト"""
    print("\n🧪 Testing LLMProvider interface...")
    
    # Mockがインターフェースを実装していることを確認
    mock = MockLLMProvider()
    assert isinstance(mock, LLMProvider)
    print("   ✅ MockLLMProvider implements LLMProvider interface")
    
    print("\n✅ All interface tests passed!")


async def test_backward_compatibility():
    """後方互換性のテスト"""
    print("\n🧪 Testing backward compatibility...")
    
    from src.services.llm.gemini_service import GeminiService
    
    # GeminiServiceがインポートできることを確認
    assert GeminiService is not None
    print("   ✅ GeminiService imports successfully")
    
    # メソッドが存在することを確認
    assert hasattr(GeminiService, "generate")
    assert hasattr(GeminiService, "generate_json")
    assert hasattr(GeminiService, "generate_with_context")
    print("   ✅ All backward compatibility methods exist")
    
    print("\n✅ Backward compatibility maintained!")


async def main():
    """すべてのテストを実行"""
    print("=" * 60)
    print("Phase 1: Provider Layer - Manual Tests")
    print("=" * 60)
    
    try:
        await test_mock_llm_provider()
        await test_interface()
        await test_backward_compatibility()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print("\nPhase 1 is complete and ready for Phase 2.")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

