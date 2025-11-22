"""設定管理のテスト"""

import pytest
import os
from pydantic import ValidationError
from src.core.config import (
    Settings,
    DevelopmentSettings,
    ProductionSettings,
    StagingSettings,
    get_settings,
    validate_settings
)


class TestSettings:
    """Settings クラスのテスト"""
    
    def test_settings_with_required_fields(self):
        """必須フィールドが設定されている場合のテスト"""
        settings = Settings(gemini_api_key="test-api-key-12345")
        
        assert settings.gemini_api_key == "test-api-key-12345"
        assert settings.app_name == "LangGraph Training"
        assert settings.environment == "development"
        assert settings.debug is True
    
    def test_settings_without_required_fields(self):
        """必須フィールドが欠けている場合のテスト"""
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        # gemini_api_keyが必須であることを確認
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('gemini_api_key',) for error in errors)
    
    def test_settings_with_all_fields(self):
        """全フィールドが設定されている場合のテスト"""
        settings = Settings(
            gemini_api_key="test-key",
            slack_token="slack-token",
            jira_token="jira-token",
            jira_server="https://test.atlassian.net",
            jira_email="test@example.com",
            supabase_url="https://test.supabase.co",
            supabase_key="supabase-key",
            embedding_dimension=512,
            max_chunk_size=2000,
            chunk_overlap=100,
            similarity_threshold=0.8,
            max_retrieval_results=10
        )
        
        assert settings.gemini_api_key == "test-key"
        assert settings.slack_token == "slack-token"
        assert settings.jira_token == "jira-token"
        assert settings.embedding_dimension == 512
        assert settings.max_chunk_size == 2000
    
    def test_embedding_dimension_validation(self):
        """埋め込み次元数のバリデーションテスト"""
        # 正常な範囲
        settings = Settings(gemini_api_key="test", embedding_dimension=768)
        assert settings.embedding_dimension == 768
        
        # 範囲外（小さすぎる）
        with pytest.raises(ValidationError):
            Settings(gemini_api_key="test", embedding_dimension=0)
        
        # 範囲外（大きすぎる）
        with pytest.raises(ValidationError):
            Settings(gemini_api_key="test", embedding_dimension=5000)
    
    def test_chunk_overlap_validation(self):
        """チャンクオーバーラップのバリデーションテスト"""
        # 正常: chunk_overlap < max_chunk_size
        settings = Settings(
            gemini_api_key="test",
            max_chunk_size=1000,
            chunk_overlap=200
        )
        assert settings.chunk_overlap == 200
        
        # エラー: chunk_overlap >= max_chunk_size
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                gemini_api_key="test",
                max_chunk_size=1000,
                chunk_overlap=1000
            )
        assert "chunk_overlap" in str(exc_info.value)
    
    def test_jira_server_validation(self):
        """JiraサーバーURLのバリデーションテスト"""
        # 正常: https://で始まる
        settings = Settings(
            gemini_api_key="test",
            jira_server="https://test.atlassian.net"
        )
        assert settings.jira_server == "https://test.atlassian.net"
        
        # 正常: http://で始まる
        settings = Settings(
            gemini_api_key="test",
            jira_server="http://localhost:8080"
        )
        assert settings.jira_server == "http://localhost:8080"
        
        # エラー: プロトコルなし
        with pytest.raises(ValidationError):
            Settings(
                gemini_api_key="test",
                jira_server="test.atlassian.net"
            )
    
    def test_supabase_url_validation(self):
        """Supabase URLのバリデーションテスト"""
        # 正常: https://で始まる
        settings = Settings(
            gemini_api_key="test",
            supabase_url="https://test.supabase.co"
        )
        assert settings.supabase_url == "https://test.supabase.co"
        
        # エラー: http://で始まる（httpsのみ許可）
        with pytest.raises(ValidationError):
            Settings(
                gemini_api_key="test",
                supabase_url="http://test.supabase.co"
            )
    
    def test_similarity_threshold_validation(self):
        """類似度閾値のバリデーションテスト"""
        # 正常: 0.0 - 1.0の範囲
        settings = Settings(
            gemini_api_key="test",
            similarity_threshold=0.7
        )
        assert settings.similarity_threshold == 0.7
        
        # 範囲外
        with pytest.raises(ValidationError):
            Settings(gemini_api_key="test", similarity_threshold=1.5)
        
        with pytest.raises(ValidationError):
            Settings(gemini_api_key="test", similarity_threshold=-0.1)


class TestEnvironmentSpecificSettings:
    """環境別設定のテスト"""
    
    def test_development_settings(self):
        """開発環境設定のテスト"""
        settings = DevelopmentSettings(gemini_api_key="test")
        
        assert settings.environment == "development"
        assert settings.debug is True
        assert settings.log_level == "DEBUG"
    
    def test_production_settings(self):
        """本番環境設定のテスト"""
        settings = ProductionSettings(gemini_api_key="test")
        
        assert settings.environment == "production"
        assert settings.debug is False
        assert settings.log_level == "INFO"
    
    def test_staging_settings(self):
        """ステージング環境設定のテスト"""
        settings = StagingSettings(gemini_api_key="test")
        
        assert settings.environment == "staging"
        assert settings.debug is False
        assert settings.log_level == "INFO"


class TestGetSettings:
    """get_settings 関数のテスト"""
    
    def test_get_settings_default(self, monkeypatch):
        """デフォルト設定の取得テスト"""
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("ENVIRONMENT", "development")
        
        # キャッシュをクリア
        get_settings.cache_clear()
        
        settings = get_settings()
        assert settings.environment == "development"
        assert settings.gemini_api_key == "test-key"
    
    def test_get_settings_development(self, monkeypatch):
        """開発環境設定の取得テスト"""
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        get_settings.cache_clear()
        
        settings = get_settings("development")
        assert settings.environment == "development"
        assert settings.debug is True
    
    def test_get_settings_production(self, monkeypatch):
        """本番環境設定の取得テスト"""
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        get_settings.cache_clear()
        
        settings = get_settings("production")
        assert settings.environment == "production"
        assert settings.debug is False
    
    def test_get_settings_caching(self, monkeypatch):
        """設定のキャッシングテスト"""
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        get_settings.cache_clear()
        
        settings1 = get_settings("development")
        settings2 = get_settings("development")
        
        # 同じインスタンスが返される（キャッシュされている）
        assert settings1 is settings2


class TestHelperMethods:
    """ヘルパーメソッドのテスト"""
    
    def test_is_production(self):
        """is_production メソッドのテスト"""
        dev_settings = DevelopmentSettings(gemini_api_key="test")
        prod_settings = ProductionSettings(gemini_api_key="test")
        
        assert dev_settings.is_production() is False
        assert prod_settings.is_production() is True
    
    def test_is_development(self):
        """is_development メソッドのテスト"""
        dev_settings = DevelopmentSettings(gemini_api_key="test")
        prod_settings = ProductionSettings(gemini_api_key="test")
        
        assert dev_settings.is_development() is True
        assert prod_settings.is_development() is False
    
    def test_has_supabase_config(self):
        """has_supabase_config メソッドのテスト"""
        # Supabase設定あり
        settings_with = Settings(
            gemini_api_key="test",
            supabase_url="https://test.supabase.co",
            supabase_key="test-key"
        )
        assert settings_with.has_supabase_config() is True
        
        # Supabase設定なし
        settings_without = Settings(gemini_api_key="test")
        assert settings_without.has_supabase_config() is False
        
        # 部分的な設定（URLのみ）
        settings_partial = Settings(
            gemini_api_key="test",
            supabase_url="https://test.supabase.co"
        )
        assert settings_partial.has_supabase_config() is False
    
    def test_has_jira_config(self):
        """has_jira_config メソッドのテスト"""
        # Jira設定あり
        settings_with = Settings(
            gemini_api_key="test",
            jira_token="token",
            jira_server="https://test.atlassian.net",
            jira_email="test@example.com"
        )
        assert settings_with.has_jira_config() is True
        
        # Jira設定なし
        settings_without = Settings(gemini_api_key="test")
        assert settings_without.has_jira_config() is False
        
        # 部分的な設定
        settings_partial = Settings(
            gemini_api_key="test",
            jira_token="token"
        )
        assert settings_partial.has_jira_config() is False
    
    def test_get_log_config(self):
        """get_log_config メソッドのテスト"""
        settings = Settings(
            gemini_api_key="test",
            log_level="DEBUG"
        )
        
        log_config = settings.get_log_config()
        
        assert log_config['level'] == "DEBUG"
        assert 'format' in log_config
        assert 'datefmt' in log_config


class TestValidateSettings:
    """validate_settings 関数のテスト"""
    
    def test_validate_settings_success(self, monkeypatch):
        """設定検証が成功する場合のテスト"""
        # 最小限の有効な設定
        from src.core import config
        monkeypatch.setattr(
            config,
            'settings',
            Settings(gemini_api_key="test-key")
        )
        
        assert validate_settings() is True
    
    def test_validate_settings_jira_incomplete(self, monkeypatch):
        """Jira設定が不完全な場合のテスト"""
        from src.core import config
        
        # jira_tokenがあるがjira_serverがない
        monkeypatch.setattr(
            config,
            'settings',
            Settings(
                gemini_api_key="test-key",
                jira_token="token"
                # jira_server と jira_email がない
            )
        )
        
        assert validate_settings() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

