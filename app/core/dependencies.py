from typing import Dict, Any
from app.core.config import settings


def get_api_keys() -> Dict[str, Any]:
    """Get API keys and configuration"""
    return {
        "gemini_api_key": settings.gemini_api_key,
        "slack_token": settings.slack_token,
        "jira_token": settings.jira_token,
        "jira_server": settings.jira_server,
        "jira_email": settings.jira_email,
    }


def validate_gemini_key() -> str:
    """Validate and return Gemini API key"""
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured")
    return settings.gemini_api_key


def validate_slack_token() -> str:
    """Validate and return Slack token"""
    if not settings.slack_token:
        raise ValueError("SLACK_TOKEN is not configured")
    return settings.slack_token


def validate_slack_token_safe() -> str:
    """Safely validate and return Slack token"""
    if not settings.slack_token:
        return "mock_slack_token"  # Return mock token for testing
    return settings.slack_token


def validate_jira_config() -> Dict[str, str]:
    """Validate and return Jira configuration"""
    if not all([settings.jira_token, settings.jira_server, settings.jira_email]):
        raise ValueError("Jira configuration is incomplete (JIRA_TOKEN, JIRA_SERVER, JIRA_EMAIL required)")

    return {
        "token": settings.jira_token,
        "server": settings.jira_server,
        "email": settings.jira_email,
    }


def validate_jira_config_safe() -> Dict[str, str]:
    """Safely validate and return Jira configuration"""
    if not all([settings.jira_token, settings.jira_server, settings.jira_email]):
        return {
            "token": "mock_jira_token",
            "server": "https://mock.atlassian.net",
            "email": "mock@example.com",
        }

    return {
        "token": settings.jira_token,
        "server": settings.jira_server,
        "email": settings.jira_email,
    }