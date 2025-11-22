"""Settings Management with Pydantic Settings

このモジュールは、pydantic-settingsを使用した型安全な設定管理を提供します。

環境変数からの自動読み込み、型検証、デフォルト値の設定などをサポートします。

Example:
    >>> from src.core.config import settings
    >>> print(settings.gemini_api_key)
    >>> print(settings.app_name)
    
    >>> # 環境別の設定
    >>> from src.core.config import get_settings
    >>> dev_settings = get_settings(env="development")
"""

from typing import Optional, Literal
from pydantic import Field, field_validator, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """アプリケーション設定
    
    pydantic-settingsを使用した型安全な設定管理。
    環境変数から自動的に値を読み込み、型検証を行います。
    
    Attributes:
        app_name: アプリケーション名
        environment: 実行環境（development, staging, production）
        debug: デバッグモード
        log_level: ロギングレベル
        
        gemini_api_key: Gemini APIキー（必須）
        slack_token: Slack APIトークン
        
        jira_token: Jira APIトークン
        jira_server: JiraサーバーURL
        jira_email: Jira認証用メールアドレス
        
        embedding_model: 使用する埋め込みモデル
        embedding_dimension: 埋め込みベクトルの次元数
        gemini_embedding_model: Gemini埋め込みモデル名
        
        supabase_url: Supabase プロジェクトURL
        supabase_key: Supabase APIキー
        supabase_service_key: Supabase サービスキー
        
        max_chunk_size: ドキュメント分割時の最大チャンクサイズ
        chunk_overlap: チャンク間のオーバーラップサイズ
        
        similarity_threshold: 類似度検索の閾値
        max_retrieval_results: 最大検索結果数
    
    Example:
        >>> settings = Settings()
        >>> print(settings.gemini_api_key)
        >>> print(settings.model_dump())
    """
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',  # 未定義の環境変数を無視
        validate_default=True,  # デフォルト値も検証
    )
    
    # ============================================================================
    # Application Settings
    # ============================================================================
    
    app_name: str = Field(
        default="LangGraph Training",
        description="アプリケーション名"
    )
    
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="実行環境"
    )
    
    debug: bool = Field(
        default=True,
        description="デバッグモード"
    )
    
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="ロギングレベル"
    )
    
    # ============================================================================
    # API Keys & Tokens
    # ============================================================================
    
    gemini_api_key: str = Field(
        ...,  # 必須フィールド
        description="Gemini APIキー（必須）",
        min_length=1
    )
    
    slack_token: Optional[str] = Field(
        default=None,
        description="Slack APIトークン"
    )
    
    # ============================================================================
    # Jira Configuration
    # ============================================================================
    
    jira_token: Optional[str] = Field(
        default=None,
        description="Jira APIトークン"
    )
    
    jira_server: Optional[str] = Field(
        default=None,
        description="JiraサーバーURL",
        examples=["https://your-domain.atlassian.net"]
    )
    
    jira_email: Optional[str] = Field(
        default=None,
        description="Jira認証用メールアドレス"
    )
    
    # ============================================================================
    # RAG Configuration
    # ============================================================================
    
    embedding_model: str = Field(
        default="gemini",
        description="使用する埋め込みモデル"
    )
    
    embedding_dimension: int = Field(
        default=768,
        description="埋め込みベクトルの次元数",
        ge=1,  # 1以上
        le=4096  # 4096以下
    )
    
    gemini_embedding_model: str = Field(
        default="models/embedding-001",
        description="Gemini埋め込みモデル名"
    )
    
    # ============================================================================
    # Supabase Configuration
    # ============================================================================
    
    supabase_url: Optional[str] = Field(
        default=None,
        description="Supabase プロジェクトURL",
        examples=["https://xxxxx.supabase.co"]
    )
    
    supabase_key: Optional[str] = Field(
        default=None,
        description="Supabase APIキー"
    )
    
    supabase_service_key: Optional[str] = Field(
        default=None,
        description="Supabase サービスキー"
    )
    
    # ============================================================================
    # Document Processing
    # ============================================================================
    
    max_chunk_size: int = Field(
        default=1000,
        description="ドキュメント分割時の最大チャンクサイズ",
        ge=100,  # 100以上
        le=10000  # 10000以下
    )
    
    chunk_overlap: int = Field(
        default=200,
        description="チャンク間のオーバーラップサイズ",
        ge=0,  # 0以上
        le=1000  # 1000以下
    )
    
    # ============================================================================
    # Search & Retrieval
    # ============================================================================
    
    similarity_threshold: float = Field(
        default=0.7,
        description="類似度検索の閾値",
        ge=0.0,  # 0.0以上
        le=1.0  # 1.0以下
    )
    
    max_retrieval_results: int = Field(
        default=5,
        description="最大検索結果数",
        ge=1,  # 1以上
        le=100  # 100以下
    )
    
    # ============================================================================
    # Validators
    # ============================================================================
    
    @field_validator('chunk_overlap')
    @classmethod
    def validate_chunk_overlap(cls, v: int, info) -> int:
        """チャンクオーバーラップの検証
        
        オーバーラップサイズがチャンクサイズより小さいことを確認
        """
        # info.dataからmax_chunk_sizeを取得
        max_chunk_size = info.data.get('max_chunk_size', 1000)
        if v >= max_chunk_size:
            raise ValueError(
                f"chunk_overlap ({v}) must be less than max_chunk_size ({max_chunk_size})"
            )
        return v
    
    @field_validator('jira_server')
    @classmethod
    def validate_jira_server(cls, v: Optional[str]) -> Optional[str]:
        """JiraサーバーURLの検証"""
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError("jira_server must start with http:// or https://")
        return v
    
    @field_validator('supabase_url')
    @classmethod
    def validate_supabase_url(cls, v: Optional[str]) -> Optional[str]:
        """Supabase URLの検証"""
        if v and not v.startswith('https://'):
            raise ValueError("supabase_url must start with https://")
        return v
    
    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """環境設定の検証"""
        logger.info(f"Running in {v} environment")
        return v
    
    # ============================================================================
    # Helper Methods
    # ============================================================================
    
    def is_production(self) -> bool:
        """本番環境かどうか"""
        return self.environment == "production"
    
    def is_development(self) -> bool:
        """開発環境かどうか"""
        return self.environment == "development"
    
    def has_supabase_config(self) -> bool:
        """Supabase設定が完全かどうか"""
        return bool(self.supabase_url and self.supabase_key)
    
    def has_jira_config(self) -> bool:
        """Jira設定が完全かどうか"""
        return bool(self.jira_token and self.jira_server and self.jira_email)
    
    def get_log_config(self) -> dict:
        """ロギング設定を取得"""
        return {
            'level': self.log_level,
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }


# ============================================================================
# Environment-specific Settings
# ============================================================================

class DevelopmentSettings(Settings):
    """開発環境用設定
    
    デバッグモードが有効で、ログレベルがDEBUGに設定されます。
    """
    model_config = SettingsConfigDict(
        env_file='.env.development',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )
    
    environment: Literal["development"] = "development"
    debug: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "DEBUG"


class ProductionSettings(Settings):
    """本番環境用設定
    
    デバッグモードが無効で、ログレベルがINFOに設定されます。
    """
    model_config = SettingsConfigDict(
        env_file='.env.production',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )
    
    environment: Literal["production"] = "production"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


class StagingSettings(Settings):
    """ステージング環境用設定
    
    本番に近い設定で、ログレベルがINFOに設定されます。
    """
    model_config = SettingsConfigDict(
        env_file='.env.staging',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )
    
    environment: Literal["staging"] = "staging"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


# ============================================================================
# Settings Factory
# ============================================================================

@lru_cache()
def get_settings(env: Optional[str] = None) -> Settings:
    """環境に応じた設定を取得
    
    Args:
        env: 環境名（development, staging, production）
            省略時は環境変数ENVIRONMENTから取得
    
    Returns:
        Settings: 環境に応じた設定インスタンス
    
    Example:
        >>> # デフォルト設定
        >>> settings = get_settings()
        >>> 
        >>> # 開発環境用設定
        >>> dev_settings = get_settings("development")
        >>> 
        >>> # 本番環境用設定
        >>> prod_settings = get_settings("production")
    """
    import os
    
    if env is None:
        env = os.getenv('ENVIRONMENT', 'development')
    
    settings_map = {
        'development': DevelopmentSettings,
        'staging': StagingSettings,
        'production': ProductionSettings,
    }
    
    settings_class = settings_map.get(env, Settings)
    
    try:
        instance = settings_class()
        logger.info(f"Settings loaded successfully for environment: {env}")
        return instance
    except ValidationError as e:
        logger.error(f"Settings validation error: {e}")
        raise


# ============================================================================
# Global Settings Instance
# ============================================================================

# グローバル設定インスタンス（後方互換性のため）
try:
    settings = get_settings()
except Exception as e:
    logger.error(f"Failed to load settings: {e}")
    # フォールバック: 最小限の設定で起動を試みる
    logger.warning("Using fallback settings with minimal configuration")
    
    # GEMINI_API_KEYだけは必須なので、なければエラー
    import os
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError(
            "GEMINI_API_KEY is required. Please set it in .env file or environment variables."
        ) from e
    
    settings = Settings(gemini_api_key=os.getenv("GEMINI_API_KEY", ""))


# ============================================================================
# Utilities
# ============================================================================

def validate_settings() -> bool:
    """設定の妥当性を検証
    
    Returns:
        bool: 全ての必須設定が正しく構成されている場合True
    
    Example:
        >>> if validate_settings():
        ...     print("All settings are valid")
    """
    try:
        # 必須フィールドの確認
        assert settings.gemini_api_key, "GEMINI_API_KEY is required"
        
        # 依存関係の確認
        if settings.jira_token:
            assert settings.jira_server, "JIRA_SERVER is required when JIRA_TOKEN is set"
            assert settings.jira_email, "JIRA_EMAIL is required when JIRA_TOKEN is set"
        
        if settings.supabase_key:
            assert settings.supabase_url, "SUPABASE_URL is required when SUPABASE_KEY is set"
        
        logger.info("Settings validation passed")
        return True
        
    except AssertionError as e:
        logger.error(f"Settings validation failed: {e}")
        return False


def print_settings_summary():
    """設定のサマリーを表示（デバッグ用）
    
    機密情報はマスクして表示します。
    """
    print("=" * 70)
    print("  Settings Summary")
    print("=" * 70)
    print(f"App Name:        {settings.app_name}")
    print(f"Environment:     {settings.environment}")
    print(f"Debug Mode:      {settings.debug}")
    print(f"Log Level:       {settings.log_level}")
    print()
    print("API Keys:")
    print(f"  Gemini:        {'***' + settings.gemini_api_key[-4:] if settings.gemini_api_key else 'Not set'}")
    print(f"  Slack:         {'***' + settings.slack_token[-4:] if settings.slack_token else 'Not set'}")
    print(f"  Jira:          {'***' + settings.jira_token[-4:] if settings.jira_token else 'Not set'}")
    print()
    print("RAG Configuration:")
    print(f"  Embedding Model:     {settings.embedding_model}")
    print(f"  Embedding Dimension: {settings.embedding_dimension}")
    print(f"  Max Chunk Size:      {settings.max_chunk_size}")
    print(f"  Chunk Overlap:       {settings.chunk_overlap}")
    print()
    print("Supabase:")
    print(f"  Configured:    {settings.has_supabase_config()}")
    if settings.supabase_url:
        print(f"  URL:           {settings.supabase_url}")
    print()
    print("=" * 70)


if __name__ == "__main__":
    # 設定のテスト実行
    print_settings_summary()
    
    if validate_settings():
        print("\n✅ All settings are valid!")
    else:
        print("\n❌ Settings validation failed!")
