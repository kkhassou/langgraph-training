from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os

from app.core.config import settings
from app.api import routes_nodes

# Create FastAPI app
app = FastAPI(
    title="LangGraph Training API (Minimal)",
    description="""
    ## LangGraph Training Workshop API - Minimal Version

    This minimal version provides access to core LangGraph functionality:

    ### Available Features:
    - **Gemini LLM**: Text generation using Google Gemini
    - **PowerPoint Ingest**: Extract text from PowerPoint presentations

    ### Getting Started:
    1. Configure your GEMINI_API_KEY in the `.env` file
    2. Try the PowerPoint ingest functionality
    3. Test the Gemini LLM integration

    Note: Slack and Jira integrations are temporarily disabled due to missing dependencies.
    """,
    version="1.0.0-minimal",
    contact={
        "name": "LangGraph Training Team",
        "email": "training@example.com",
    }
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes_nodes.router)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with HTML documentation"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LangGraph Training API - Minimal</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
            h2 { color: #555; margin-top: 30px; }
            .endpoint { background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #4CAF50; }
            .method { background: #4CAF50; color: white; padding: 3px 8px; border-radius: 3px; font-size: 12px; }
            a { color: #4CAF50; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .footer { margin-top: 40px; text-align: center; color: #666; border-top: 1px solid #eee; padding-top: 20px; }
            .warning { background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 LangGraph Training API - Minimal</h1>
            <p>Welcome to the minimal version of the LangGraph Training Workshop API!</p>

            <div class="warning">
                <strong>⚠️ Note:</strong> This is a minimal version with Slack and Jira integrations temporarily disabled due to missing dependencies.
            </div>

            <h2>🚀 Quick Start</h2>
            <ol>
                <li>Visit <a href="/docs" target="_blank"><strong>/docs</strong></a> for the interactive Swagger UI</li>
                <li>Configure your GEMINI_API_KEY in the <code>.env</code> file</li>
                <li>Test the PowerPoint ingest functionality</li>
                <li>Try the Gemini LLM integration</li>
            </ol>

            <h2>🔧 Available Endpoints</h2>

            <div class="endpoint">
                <strong><span class="method">GET</span> <a href="/nodes/">/nodes/</a></strong><br>
                List all available nodes and their capabilities
            </div>

            <div class="endpoint">
                <strong><span class="method">POST</span> /nodes/gemini</strong><br>
                Execute Gemini LLM node for text generation
            </div>

            <div class="endpoint">
                <strong><span class="method">POST</span> /nodes/ppt-ingest</strong><br>
                Extract text from PowerPoint presentations
            </div>

            <h2>🔧 Installation</h2>
            <p>To enable full functionality with Slack and Jira integrations:</p>
            <pre>
pip install slack-sdk jira python-pptx
            </pre>

            <div class="footer">
                <p><strong>LangGraph Training Workshop - Minimal Version</strong> |
                   <a href="/docs">API Documentation</a></p>
            </div>
        </div>
    </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.app_name + " (Minimal)",
        "version": "1.0.0-minimal",
        "available_features": ["gemini", "ppt-ingest"]
    }


@app.get("/config")
async def get_config():
    """Get application configuration (without sensitive data)"""
    return {
        "app_name": settings.app_name,
        "debug": settings.debug,
        "configured_apis": {
            "gemini": bool(settings.gemini_api_key),
            "slack": "disabled (missing dependencies)",
            "jira": "disabled (missing dependencies)"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main_minimal:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )