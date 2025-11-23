from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os
import time

from src.core.config import settings
from src.core.logging_config import (
    setup_logging,
    get_structured_logger,
    set_request_id,
    clear_request_id
)
from src.api import routes_nodes, routes_workflows, routes_slack_webhook, routes_slack_commands

# ロギング設定を初期化
setup_logging()
structured_logger = get_structured_logger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """構造化ロギングミドルウェア
    
    すべてのリクエストに対して：
    - リクエストIDを自動生成
    - リクエスト/レスポンス時間を計測
    - 構造化ログを記録
    """
    
    async def dispatch(self, request: Request, call_next):
        # リクエストIDを生成・設定
        request_id = set_request_id()
        
        # 開始時間
        start_time = time.time()
        
        # リクエストログ
        structured_logger.info(
            f"Request started: {request.method} {request.url.path}",
            event_type="request_start",
            http_method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_host=request.client.host if request.client else "unknown"
        )
        
        try:
            # リクエストを処理
            response = await call_next(request)
            
            # レスポンス時間を計測
            duration = time.time() - start_time
            
            # レスポンスログ
            structured_logger.api_request(
                request.method,
                request.url.path,
                response.status_code,
                duration
            )
            
            # レスポンスヘッダーにリクエストIDを追加
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # エラーログ
            duration = time.time() - start_time
            structured_logger.error(
                f"Request failed: {request.method} {request.url.path}",
                event_type="request_error",
                http_method=request.method,
                path=request.url.path,
                duration_seconds=duration,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            raise
        finally:
            # リクエストIDをクリア
            clear_request_id()


# Create FastAPI app
app = FastAPI(
    title="LangGraph Training API",
    description="""
    ## LangGraph Training Workshop API

    このAPIは、トレーニングワークショップ用の様々なLangGraphノードとワークフローへのアクセスを提供します。

    ### 機能:
    - **ノード** (`/nodes/`): 個別の処理ユニット（LLM、PowerPoint、Slack、Gmail など）
    - **ワークフロー** (`/workflows/`): 複数のノードを組み合わせた完全なワークフロー
      - 基本ワークフロー: SimpleChatGraph, PPTSummaryGraph
      - パターン: Reflection, Chain of Thought
      - 高度: RAG, TODO 処理
    - **可視化**: ワークフロー可視化用の Mermaid 図

    ### はじめに:
    1. `.env` ファイルで API キーを設定してください
    2. 個別ノードを試して機能を理解してください（`/nodes/`）
    3. ワークフローを実行して複数ノードの組み合わせを体験してください（`/workflows/`）
    4. 図で可視化してワークフロー構造を理解してください（`/workflows/diagrams/{name}`）

    ### ワークショップの流れ:
    - ステップ1: 個別ノードをテスト（`/nodes/`）
    - ステップ2: 完全なワークフローを実行（`/workflows/`）
    - ステップ3: デザインパターンを適用（`/workflows/reflection`, `/workflows/chain-of-thought`）
    - ステップ4: 図で可視化（`/workflows/diagrams/{workflow_name}`）

    """,
    version="1.0.0",
    contact={
        "name": "LangGraph Training Team",
        "email": "training@example.com",
    }
)

# ロギングミドルウェアを追加（最初に追加）
app.add_middleware(LoggingMiddleware)

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
app.include_router(routes_workflows.router)
app.include_router(routes_slack_webhook.router)
app.include_router(routes_slack_commands.router)


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
                <strong><span class="method">GET</span> <a href="/workflows/">/workflows/</a></strong><br>
                List all available workflows
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
                <strong><span class="method">POST</span> /workflows/ppt-summary</strong><br>
                Complete workflow: PowerPoint → Text Extraction → AI Summary
            </div>

            <div class="endpoint">
                <strong><span class="method">POST</span> /workflows/reflection</strong><br>
                Advanced pattern: Iterative improvement through self-reflection
            </div>

            <div class="endpoint">
                <strong><span class="method">POST</span> /workflows/todo</strong><br>
                Advanced workflow: Parse TODOs from email, generate advice, send response
            </div>

            <div class="endpoint">
                <strong><span class="method">GET</span> /workflows/diagrams/{workflow_name}</strong><br>
                Get Mermaid diagram visualization for any workflow
            </div>

            <h2>📚 Workshop Progression</h2>
            <ol>
                <li><strong>Node Exploration</strong>: Test individual components at <code>/nodes/</code></li>
                <li><strong>Workflow Assembly</strong>: Combine nodes into workflows at <code>/workflows/</code></li>
                <li><strong>Pattern Application</strong>: Use advanced design patterns (Reflection, Chain of Thought)</li>
                <li><strong>Visualization</strong>: Understand workflow structure with Mermaid diagrams</li>
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