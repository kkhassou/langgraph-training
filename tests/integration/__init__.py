"""Integration Tests

エンドツーエンドの統合テストを提供します。

これらのテストは実際のプロバイダーやサービスを使用する場合があり、
ユニットテストよりも実行時間が長くなる可能性があります。

テストの実行:
    # 統合テストのみ実行
    pytest tests/integration/ -v

    # 統合テストをスキップ
    pytest -m "not integration"

    # カバレッジ付きで実行
    pytest tests/integration/ --cov=src --cov-report=html
"""

