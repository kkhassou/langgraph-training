"""
LLM Service Layer - 廃止のお知らせ

⚠️  このモジュールは廃止されました。

LLM関連の機能は src.core.providers.llm に統合されました。
新しいコードでは以下を使用してください：

旧:
    from src.services.llm.gemini_service import GeminiService
    response = await GeminiService.generate(prompt)

新:
    from src.core.factory import ProviderFactory
    provider = ProviderFactory.get_default_llm_provider()
    response = await provider.generate(prompt)

または直接:
    from src.providers.llm.gemini import GeminiProvider
    from src.core.config import settings
    provider = GeminiProvider(api_key=settings.gemini_api_key)
    response = await provider.generate(prompt)

詳細は以下を参照してください:
- src/core/providers/llm.py - LLMProviderインターフェース
- src/providers/llm/gemini.py - Gemini実装
- src/core/factory.py - ProviderFactory
- REFACTORING_COMPLETE.md - リファクタリングドキュメント
"""

# 後方互換性のための警告
import warnings

warnings.warn(
    "src.services.llm module is deprecated. "
    "Use src.core.providers.llm and src.core.factory instead. "
    "See src/services/llm/__init__.py for migration guide.",
    DeprecationWarning,
    stacklevel=2
)
