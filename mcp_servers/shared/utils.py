"""
Shared utilities for MCP servers
"""
import json
import logging
from typing import Any, Dict, Optional, Union
from datetime import datetime


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Setup logger for MCP servers"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def safe_json_loads(data: str, default: Any = None) -> Any:
    """Safely load JSON data with fallback"""
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(data: Any, default: str = "{}") -> str:
    """Safely dump data to JSON with fallback"""
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return default


def format_datetime(dt: Union[str, datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime string consistently"""
    if isinstance(dt, str):
        try:
            # Try to parse ISO format
            if 'T' in dt:
                parsed_dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            else:
                parsed_dt = datetime.strptime(dt, format_str)
            return parsed_dt.strftime(format_str)
        except (ValueError, TypeError):
            return dt
    elif isinstance(dt, datetime):
        return dt.strftime(format_str)
    else:
        return str(dt)


def validate_required_env_vars(required_vars: list) -> Dict[str, Optional[str]]:
    """Validate that all required environment variables are set"""
    import os

    env_values = {}
    missing_vars = []

    for var in required_vars:
        value = os.environ.get(var)
        env_values[var] = value
        if not value:
            missing_vars.append(var)

    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    return env_values


def extract_error_message(error: Exception) -> str:
    """Extract a clean error message from various exception types"""
    error_msg = str(error)

    # Handle different error types
    if hasattr(error, 'response') and hasattr(error.response, 'get'):
        # API errors with response objects
        if isinstance(error.response, dict):
            error_msg = error.response.get('error', error_msg)
        elif hasattr(error.response, 'json'):
            try:
                json_error = error.response.json()
                error_msg = json_error.get('error', json_error.get('message', error_msg))
            except:
                pass

    return error_msg


def create_tool_result(content: Any, is_error: bool = False) -> Dict[str, Any]:
    """Create a standardized tool result"""
    return {
        "content": content if isinstance(content, str) else safe_json_dumps(content),
        "isError": is_error,
        "timestamp": datetime.now().isoformat()
    }


def parse_tool_arguments(arguments: Dict[str, Any], required: list, optional: list = None) -> Dict[str, Any]:
    """Parse and validate tool arguments"""
    optional = optional or []

    # Check required arguments
    missing_required = [arg for arg in required if arg not in arguments]
    if missing_required:
        raise ValueError(f"Missing required arguments: {', '.join(missing_required)}")

    # Extract and validate arguments
    parsed_args = {}

    for arg in required + optional:
        if arg in arguments:
            parsed_args[arg] = arguments[arg]

    return parsed_args


class MCPServerHelper:
    """Helper class for common MCP server operations"""

    def __init__(self, server_name: str):
        self.server_name = server_name
        self.logger = setup_logger(server_name)

    def log_tool_call(self, tool_name: str, arguments: Dict[str, Any]):
        """Log tool call for debugging"""
        self.logger.info(f"Tool call: {tool_name} with args: {safe_json_dumps(arguments)}")

    def log_tool_result(self, tool_name: str, success: bool, result_size: int = 0):
        """Log tool result for debugging"""
        status = "success" if success else "error"
        self.logger.info(f"Tool result: {tool_name} - {status} (size: {result_size})")

    def handle_tool_error(self, tool_name: str, error: Exception) -> Dict[str, Any]:
        """Handle and log tool errors"""
        error_msg = extract_error_message(error)
        self.logger.error(f"Tool error in {tool_name}: {error_msg}")
        return create_tool_result(f"Error in {tool_name}: {error_msg}", is_error=True)