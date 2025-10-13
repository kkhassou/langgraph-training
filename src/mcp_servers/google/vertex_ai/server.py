"""Google Vertex AI MCP Server - Provides tools to interact with Vertex AI API

This server exposes tools for:
- Text generation with Gemini models
- Chat conversations with Gemini
- Text embeddings
- Model management
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

# Import MCP SDK
try:
    from mcp.server.models import InitializationOptions
    import mcp.types as types
    from mcp.server import NotificationOptions, Server
    import mcp.server.stdio
    MCP_AVAILABLE = True
    logger.info("MCP SDK imported successfully")
except ImportError as e:
    logger.error(f"Failed to import MCP SDK: {e}")
    MCP_AVAILABLE = False
    sys.exit(1)

# Import Google Cloud Vertex AI
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel, ChatSession, Part
    from vertexai.language_models import TextEmbeddingModel
    from google.oauth2 import service_account
    from google.auth import default
    VERTEX_AI_AVAILABLE = True
    logger.info("Vertex AI client imported successfully")
except ImportError as e:
    logger.error(f"Failed to import Vertex AI client: {e}")
    VERTEX_AI_AVAILABLE = False
    sys.exit(1)

# Global Vertex AI configuration
PROJECT_ID = None
LOCATION = "us-central1"

async def init_vertex_ai_client():
    """Initialize Vertex AI client"""
    global PROJECT_ID

    try:
        # Get project ID from environment
        PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("GCP_PROJECT_ID"))

        if not PROJECT_ID:
            logger.warning("No project ID found in environment, attempting to use default credentials")
            credentials, project = default()
            PROJECT_ID = project

        if not PROJECT_ID:
            raise ValueError("Google Cloud Project ID not found. Set GOOGLE_CLOUD_PROJECT environment variable.")

        logger.info(f"Using project: {PROJECT_ID}")

        # Initialize Vertex AI
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        logger.info("Vertex AI client initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Vertex AI client: {e}")
        raise

# Create MCP server instance
server = Server("google-vertex-ai-mcp")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Vertex AI tools"""
    return [
        types.Tool(
            name="generate_text",
            description="Generate text using Gemini model",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text prompt for generation"
                    },
                    "model": {
                        "type": "string",
                        "description": "Model name (default: gemini-1.5-flash)"
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Temperature (0.0-2.0, default: 0.7)"
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum output tokens (default: 1024)"
                    }
                },
                "required": ["prompt"]
            }
        ),
        types.Tool(
            name="chat",
            description="Have a conversation with Gemini model",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "User message"
                    },
                    "model": {
                        "type": "string",
                        "description": "Model name (default: gemini-1.5-flash)"
                    },
                    "history": {
                        "type": "array",
                        "description": "Conversation history (optional)",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["message"]
            }
        ),
        types.Tool(
            name="generate_embeddings",
            description="Generate text embeddings",
            inputSchema={
                "type": "object",
                "properties": {
                    "texts": {
                        "type": "array",
                        "description": "List of texts to embed",
                        "items": {"type": "string"}
                    },
                    "model": {
                        "type": "string",
                        "description": "Model name (default: text-embedding-004)"
                    }
                },
                "required": ["texts"]
            }
        ),
        types.Tool(
            name="list_models",
            description="List available Gemini models",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests"""

    if not PROJECT_ID:
        await init_vertex_ai_client()

    try:
        if name == "generate_text":
            return await generate_text_tool(arguments or {})
        elif name == "chat":
            return await chat_tool(arguments or {})
        elif name == "generate_embeddings":
            return await generate_embeddings_tool(arguments or {})
        elif name == "list_models":
            return await list_models_tool(arguments or {})
        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

async def generate_text_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Generate text using Gemini model"""
    prompt = arguments.get("prompt")
    model_name = arguments.get("model", "gemini-1.5-flash")
    temperature = arguments.get("temperature", 0.7)
    max_tokens = arguments.get("max_tokens", 1024)

    if not prompt:
        return [types.TextContent(type="text", text="Error: prompt is required")]

    try:
        model = GenerativeModel(model_name)

        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )

        response_text = f"Model: {model_name}\n\n"
        response_text += f"Response:\n{response.text}"

        return [types.TextContent(type="text", text=response_text)]

    except Exception as error:
        logger.error(f"Error generating text: {error}")
        return [types.TextContent(type="text", text=f"Error generating text: {error}")]

async def chat_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Have a conversation with Gemini model"""
    message = arguments.get("message")
    model_name = arguments.get("model", "gemini-1.5-flash")
    history = arguments.get("history", [])

    if not message:
        return [types.TextContent(type="text", text="Error: message is required")]

    try:
        model = GenerativeModel(model_name)
        chat = model.start_chat()

        # Add history if provided
        if history:
            for item in history:
                role = item.get("role")
                content = item.get("content")
                if role == "user":
                    chat.send_message(content)

        # Send current message
        response = chat.send_message(message)

        response_text = f"Model: {model_name}\n\n"
        response_text += f"Assistant: {response.text}"

        return [types.TextContent(type="text", text=response_text)]

    except Exception as error:
        logger.error(f"Error in chat: {error}")
        return [types.TextContent(type="text", text=f"Error in chat: {error}")]

async def generate_embeddings_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Generate text embeddings"""
    texts = arguments.get("texts", [])
    model_name = arguments.get("model", "text-embedding-004")

    if not texts:
        return [types.TextContent(type="text", text="Error: texts array is required")]

    try:
        model = TextEmbeddingModel.from_pretrained(model_name)
        embeddings = model.get_embeddings(texts)

        response_text = f"Model: {model_name}\n\n"
        response_text += f"Generated {len(embeddings)} embedding(s):\n\n"

        for idx, embedding in enumerate(embeddings):
            response_text += f"Text {idx + 1}: {texts[idx][:50]}...\n"
            response_text += f"Embedding dimension: {len(embedding.values)}\n"
            response_text += f"First 5 values: {embedding.values[:5]}\n\n"

        return [types.TextContent(type="text", text=response_text)]

    except Exception as error:
        logger.error(f"Error generating embeddings: {error}")
        return [types.TextContent(type="text", text=f"Error generating embeddings: {error}")]

async def list_models_tool(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """List available Gemini models"""
    try:
        available_models = [
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro",
            "text-embedding-004",
            "text-embedding-005"
        ]

        response_text = "Available Vertex AI models:\n\n"

        response_text += "Generative Models:\n"
        response_text += "  - gemini-1.5-pro (Most capable)\n"
        response_text += "  - gemini-1.5-flash (Fast and efficient)\n"
        response_text += "  - gemini-1.0-pro (Stable)\n\n"

        response_text += "Embedding Models:\n"
        response_text += "  - text-embedding-004\n"
        response_text += "  - text-embedding-005 (Latest)\n"

        return [types.TextContent(type="text", text=response_text)]

    except Exception as error:
        logger.error(f"Error listing models: {error}")
        return [types.TextContent(type="text", text=f"Error listing models: {error}")]

async def main():
    """Main entry point for the MCP server"""
    logger.info("Starting Vertex AI MCP server...")

    # Initialize Vertex AI client
    try:
        await init_vertex_ai_client()
    except Exception as e:
        logger.error(f"Failed to initialize Vertex AI client: {e}")
        sys.exit(1)

    # Run the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Server running on stdio")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="google-vertex-ai-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
