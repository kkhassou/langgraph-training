"""
Workflows API Routes - 新3層構造対応

Atomic, Composite, Orchestrations の3層構造に基づいた
ワークフローAPIエンドポイント。
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])

# Initialize workflow instances
# Atomic
chat_workflow = ChatWorkflow()
rag_workflow = RAGQueryWorkflow()
document_extract_workflow = DocumentExtractWorkflow()

# Composite
ppt_summary_workflow = PPTSummaryWorkflow()
chain_of_thought_workflow = ChainOfThoughtWorkflow()
reflection_workflow = ReflectionWorkflow()


# ============================================================================
# Atomic Workflows - 最小の実行可能単位
# ============================================================================

@router.post("/atomic/chat", response_model=ChatOutput)
async def run_chat(input_data: ChatInput):
    """シンプルなチャットワークフロー
    
    単一のLLMノードを使用して、ユーザーメッセージに応答します。
    """
    try:
        result = await chat_workflow.run(input_data)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error_message)
        return result
    except Exception as e:
        logger.error(f"Chat workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/atomic/rag-query", response_model=RAGQueryOutput)
async def run_rag_query(input_data: RAGQueryInput):
    """RAG検索ワークフロー
    
    ベクトルデータベースから関連情報を検索し、
    LLMで拡張応答を生成します。
    """
    try:
        result = await rag_workflow.run(input_data)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error_message)
        return result
    except Exception as e:
        logger.error(f"RAG workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/atomic/document-extract", response_model=DocumentExtractOutput)
async def run_document_extract(input_data: DocumentExtractInput):
    """ドキュメント抽出ワークフロー
    
    PowerPointファイルからテキストを抽出します。
    """
    try:
        result = await document_extract_workflow.run(input_data)
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
    summary_style: str = "bullet_points"
):
    """PowerPoint要約ワークフロー
    
    PPTファイルをアップロードし、内容を要約します。
    DocumentExtract（Atomic）+ Chat（Atomic）の組み合わせ。
    """
    temp_file_path = None
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Run workflow
        result = await ppt_summary_workflow.run(
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
async def run_chain_of_thought(input_data: ChainOfThoughtInput):
    """Chain of Thought（段階的推論）ワークフロー
    
    質問を段階的に分析し、推論を深めていきます。
    Chat（Atomic）を複数回組み合わせた高度な推論。
    """
    try:
        result = await chain_of_thought_workflow.run(input_data)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error_message)
        return result
    except Exception as e:
        logger.error(f"Chain of Thought workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/composite/reflection", response_model=ReflectionOutput)
async def run_reflection(input_data: ReflectionInput):
    """Reflection（自己批判的推論）ワークフロー
    
    回答を生成し、自己批判を行い、改善を繰り返します。
    Chat（Atomic）を複数回組み合わせた洗練された推論。
    """
    try:
        result = await reflection_workflow.run(input_data)
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
