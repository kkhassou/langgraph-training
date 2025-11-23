"""
Workflows API Routes - 新3層構造対応

Atomic, Composite, Orchestrations の3層構造に基づいた
ワークフローAPIエンドポイント。

FastAPIのDepends機能を使用した依存性注入により、
テスト容易性と依存関係の明示化を実現しています。
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import tempfile
import os
import logging

# Atomic Workflows
from src.workflows.atomic.chat import ChatWorkflow, ChatInput, ChatOutput
from src.workflows.atomic.rag_query import RAGQueryWorkflow, RAGQueryInput, RAGQueryOutput
from src.workflows.atomic.document_extract import DocumentExtractWorkflow, DocumentExtractInput, DocumentExtractOutput

# Composite Workflows
from src.workflows.composite.document_analysis.ppt_summary import PPTSummaryWorkflow, PPTSummaryInput, PPTSummaryOutput
from src.workflows.composite.intelligent_chat.chain_of_thought import ChainOfThoughtWorkflow, ChainOfThoughtInput, ChainOfThoughtOutput
from src.workflows.composite.intelligent_chat.reflection import ReflectionWorkflow, ReflectionInput, ReflectionOutput

# Dependencies
from src.api.dependencies import (
    get_chat_workflow,
    get_rag_query_workflow,
    get_document_extract_workflow,
    get_ppt_summary_workflow,
    get_chain_of_thought_workflow,
    get_reflection_workflow
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])


# ============================================================================
# Atomic Workflows - 最小の実行可能単位
# ============================================================================

@router.post("/atomic/chat", response_model=ChatOutput)
async def run_chat(
    input_data: ChatInput,
    workflow: ChatWorkflow = Depends(get_chat_workflow)
):
    """シンプルなチャットワークフロー
    
    単一のLLMノードを使用して、ユーザーメッセージに応答します。
    
    依存性注入により、ChatWorkflowが自動的に提供されます。
    """
    try:
        result = await workflow.run(input_data)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error_message)
        return result
    except Exception as e:
        logger.error(f"Chat workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/atomic/rag-query", response_model=RAGQueryOutput)
async def run_rag_query(
    input_data: RAGQueryInput,
    workflow: RAGQueryWorkflow = Depends(get_rag_query_workflow)
):
    """RAG検索ワークフロー
    
    ベクトルデータベースから関連情報を検索し、
    LLMで拡張応答を生成します。
    
    依存性注入により、RAGQueryWorkflowが自動的に提供されます。
    """
    try:
        result = await workflow.run(input_data)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error_message)
        return result
    except Exception as e:
        logger.error(f"RAG workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/atomic/document-extract", response_model=DocumentExtractOutput)
async def run_document_extract(
    input_data: DocumentExtractInput,
    workflow: DocumentExtractWorkflow = Depends(get_document_extract_workflow)
):
    """ドキュメント抽出ワークフロー
    
    PowerPointファイルからテキストを抽出します。
    
    依存性注入により、DocumentExtractWorkflowが自動的に提供されます。
    """
    try:
        result = await workflow.run(input_data)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error_message)
        return result
    except Exception as e:
        logger.error(f"Document extract workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Composite Workflows - Atomicを組み合わせた複合ワークフロー
# ============================================================================

@router.post("/composite/ppt-summary", response_model=PPTSummaryOutput)
async def run_ppt_summary(
    file: UploadFile = File(...),
    summary_style: str = "bullet_points",
    workflow: PPTSummaryWorkflow = Depends(get_ppt_summary_workflow)
):
    """PowerPoint要約ワークフロー
    
    PPTファイルをアップロードし、内容を要約します。
    DocumentExtract（Atomic）+ Chat（Atomic）の組み合わせ。
    
    依存性注入により、PPTSummaryWorkflowが自動的に提供されます。
    """
    temp_file_path = None
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Run workflow
        result = await workflow.run(
            PPTSummaryInput(
                file_path=temp_file_path,
                summary_style=summary_style
            )
        )

        if not result.success:
            raise HTTPException(status_code=500, detail=result.error_message)

        return result

    except Exception as e:
        logger.error(f"PPT summary workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to remove temp file: {e}")


@router.post("/composite/chain-of-thought", response_model=ChainOfThoughtOutput)
async def run_chain_of_thought(
    input_data: ChainOfThoughtInput,
    workflow: ChainOfThoughtWorkflow = Depends(get_chain_of_thought_workflow)
):
    """Chain of Thought（段階的推論）ワークフロー
    
    質問を段階的に分析し、推論を深めていきます。
    Chat（Atomic）を複数回組み合わせた高度な推論。
    
    依存性注入により、ChainOfThoughtWorkflowが自動的に提供されます。
    """
    try:
        result = await workflow.run(input_data)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error_message)
        return result
    except Exception as e:
        logger.error(f"Chain of Thought workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/composite/reflection", response_model=ReflectionOutput)
async def run_reflection(
    input_data: ReflectionInput,
    workflow: ReflectionWorkflow = Depends(get_reflection_workflow)
):
    """Reflection（自己批判的推論）ワークフロー
    
    回答を生成し、自己批判を行い、改善を繰り返します。
    Chat（Atomic）を複数回組み合わせた洗練された推論。
    
    依存性注入により、ReflectionWorkflowが自動的に提供されます。
    """
    try:
        result = await workflow.run(input_data)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error_message)
        return result
    except Exception as e:
        logger.error(f"Reflection workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 後方互換性のためのエイリアス
# ============================================================================

@router.post("/simple-chat")
async def run_simple_chat_legacy(input_data: ChatInput):
    """後方互換性: simple-chat → atomic/chat"""
    return await run_chat(input_data)


@router.post("/ppt-summary")
async def run_ppt_summary_legacy(
    file: UploadFile = File(...),
    summary_style: str = "bullet_points"
):
    """後方互換性: ppt-summary → composite/ppt-summary"""
    return await run_ppt_summary(file, summary_style)


@router.post("/rag")
async def run_rag_legacy(input_data: RAGQueryInput):
    """後方互換性: rag → atomic/rag-query"""
    return await run_rag_query(input_data)


@router.post("/chain-of-thought")
async def run_chain_of_thought_legacy(input_data: ChainOfThoughtInput):
    """後方互換性: chain-of-thought → composite/chain-of-thought"""
    return await run_chain_of_thought(input_data)


@router.post("/reflection")
async def run_reflection_legacy(input_data: ReflectionInput):
    """後方互換性: reflection → composite/reflection"""
    return await run_reflection(input_data)
