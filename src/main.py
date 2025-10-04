from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import os

from src.core.config import settings
from src.api import routes_nodes, routes_graphs

# Create FastAPI app
app = FastAPI(
    title="LangGraph Training API",
    description="""
    ## LangGraph Training Workshop API

    このAPIは、トレーニングワークショップ用の様々なLangGraphノードとワークフローへのアクセスを提供します。

    ### 機能:
    - **ノード**: 個別の処理ユニット（LLM、PowerPoint、Slack、Jira）
    - **グラフ**: 複数のノードを組み合わせた構成済みワークフロー
    - **パターン**: ReflectionやChain of Thoughtなどの高度なパターン
    - **可視化**: ワークフロー可視化用のMermaid図

    ### はじめに:
    1. `.env`ファイルでAPIキーを設定してください
    2. 個別ノードを試して機能を理解してください
    3. 複数のノードを組み合わせたグラフワークフローを探索してください
    4. 高度なユースケース向けのデザインパターンを実験してください

    ### ワークショップの流れ:
    - ステップ1: 個別ノードをテスト（`/nodes/`）
    - ステップ2: 完全なワークフローを実行（`/graphs/`）
    - ステップ3: デザインパターンを適用（`/patterns`）
    - ステップ4: 図で可視化（`/docs/diagrams/{graph_name}`）

    """,
    version="1.0.0",
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
app.include_router(routes_graphs.router)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with HTML documentation"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LangGraph Training API</title>
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
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 LangGraph Training API</h1>
            <p>Welcome to the LangGraph Training Workshop API! This interactive platform helps you learn LangGraph through hands-on experience.</p>

            <h2>🚀 Quick Start</h2>
            <ol>
                <li>Visit <a href="/docs" target="_blank"><strong>/docs</strong></a> for the interactive Swagger UI</li>
                <li>Configure your API keys in the <code>.env</code> file</li>
                <li>Start with individual nodes to understand basic functionality</li>
                <li>Progress to graph workflows that combine multiple nodes</li>
                <li>Explore advanced patterns for complex use cases</li>
            </ol>

            <h2>=' Available Endpoints</h2>

            <div class="endpoint">
                <strong><span class="method">GET</span> <a href="/nodes/">/nodes/</a></strong><br>
                List all available nodes and their capabilities
            </div>

            <div class="endpoint">
                <strong><span class="method">GET</span> <a href="/graphs/">/graphs/</a></strong><br>
                List all available graph workflows
            </div>

            <div class="endpoint">
                <strong><span class="method">POST</span> /nodes/gemini</strong><br>
                Execute Gemini LLM node for text generation
            </div>

            <div class="endpoint">
                <strong><span class="method">POST</span> /nodes/ppt-ingest</strong><br>
                Extract text from PowerPoint presentations
            </div>

            <div class="endpoint">
                <strong><span class="method">POST</span> /graphs/ppt-summary</strong><br>
                Complete workflow: PowerPoint � Text Extraction � AI Summary
            </div>

            <div class="endpoint">
                <strong><span class="method">POST</span> /graphs/slack-report</strong><br>
                Complete workflow: Slack Messages � Analysis � Report Generation
            </div>

            <div class="endpoint">
                <strong><span class="method">POST</span> /graphs/reflection</strong><br>
                Advanced pattern: Iterative improvement through self-reflection
            </div>

            <div class="endpoint">
                <strong><span class="method">GET</span> /graphs/diagrams/{graph_name}</strong><br>
                Get Mermaid diagram visualization for any workflow
            </div>

            <h2><� Workshop Progression</h2>
            <ol>
                <li><strong>Node Exploration</strong>: Test individual components</li>
                <li><strong>Graph Assembly</strong>: Combine nodes into workflows</li>
                <li><strong>Pattern Application</strong>: Use advanced design patterns</li>
                <li><strong>Visualization</strong>: Understand workflow structure</li>
                <li><strong>Custom Development</strong>: Build your own solutions</li>
            </ol>

            <div class="footer">
                <p><strong>LangGraph Training Workshop</strong> |
                   <a href="/docs">API Documentation</a> |
                   <a href="/redoc">Alternative Docs</a></p>
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
        "app_name": settings.app_name,
        "version": "1.0.0"
    }


@app.get("/config")
async def get_config():
    """Get application configuration (without sensitive data)"""
    return {
        "app_name": settings.app_name,
        "debug": settings.debug,
        "configured_apis": {
            "gemini": bool(settings.gemini_api_key),
            "slack": bool(settings.slack_token),
            "jira": bool(settings.jira_token and settings.jira_server and settings.jira_email)
        }
    }


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail": "Endpoint not found"})


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )