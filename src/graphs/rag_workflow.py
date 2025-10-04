from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel

from src.nodes.base import NodeState
from src.nodes.rag.advanced_rag_node import AdvancedRAGNode
from src.nodes.rag.search_node import SearchNode
from src.nodes.rag.document_ingest_node import DocumentIngestNode
from src.nodes.llm.gemini import GeminiNode


class RAGWorkflowInput(BaseModel):
    """Input model for RAG workflow"""
    query: str
    collection_name: str = "default_collection"
    search_type: str = "hybrid"
    top_k: int = 5
    include_conversation: bool = True
    context_optimization: bool = True
    workflow_type: str = "simple"  # "simple", "advanced", "search_only"


class RAGWorkflowOutput(BaseModel):
    """Output model for RAG workflow"""
    answer: str = ""
    retrieved_documents: list = []
    workflow_type: str = ""
    execution_steps: list = []
    context_stats: Dict[str, Any] = {}
    success: bool = True
    error_message: str = None


class RAGWorkflow:
    """RAG workflow orchestrating different RAG strategies"""

    def __init__(self):
        self.search_node = SearchNode()
        self.advanced_rag_node = AdvancedRAGNode()
        self.document_ingest_node = DocumentIngestNode()
        self.llm_node = GeminiNode()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the RAG workflow graph"""
        workflow = StateGraph(NodeState)

        # Add nodes
        workflow.add_node("route_workflow", self._route_workflow)
        workflow.add_node("search_only", self._search_only_step)
        workflow.add_node("advanced_rag", self._advanced_rag_step)
        workflow.add_node("simple_rag", self._simple_rag_step)
        workflow.add_node("finalize_response", self._finalize_response)

        # Set entry point
        workflow.add_edge(START, "route_workflow")

        # Add conditional edges
        workflow.add_conditional_edges(
            "route_workflow",
            self._decide_next_step,
            {
                "search_only": "search_only",
                "advanced_rag": "advanced_rag",
                "simple_rag": "simple_rag"
            }
        )

        # All paths lead to finalization
        workflow.add_edge("search_only", "finalize_response")
        workflow.add_edge("advanced_rag", "finalize_response")
        workflow.add_edge("simple_rag", "finalize_response")
        workflow.add_edge("finalize_response", END)

        return workflow.compile()

    async def _route_workflow(self, state: NodeState) -> NodeState:
        """Route to appropriate workflow based on input"""
        # Handle both dict and NodeState
        state_data = state.get("data", {}) if isinstance(state, dict) else state.data
        
        workflow_type = state_data.get("workflow_type", "simple")
        state_data["execution_steps"] = ["route_workflow"]
        
        # Map workflow_type to actual route names
        workflow_mapping = {
            "simple": "simple_rag",
            "advanced": "advanced_rag",
            "search_only": "search_only"
        }
        
        state_data["routed_to"] = workflow_mapping.get(workflow_type, "simple_rag")
        
        # Return appropriate format
        if isinstance(state, dict):
            state["data"] = state_data
            return state
        else:
            state.data = state_data
            return state

    def _decide_next_step(self, state: NodeState) -> str:
        """Decide which workflow step to execute next"""
        # Handle both dict and NodeState
        state_data = state.get("data", {}) if isinstance(state, dict) else state.data
        return state_data.get("routed_to", "simple_rag")

    async def _search_only_step(self, state: NodeState) -> NodeState:
        """Execute search-only workflow"""
        try:
            # Convert dict to NodeState if needed
            if isinstance(state, dict):
                node_state = NodeState(**state)
            else:
                node_state = state
                
            result = await self.search_node.execute(node_state)
            result.data["execution_steps"].append("search_only")
            
            # Return as dict if input was dict
            if isinstance(state, dict):
                return result.model_dump()
            return result
        except Exception as e:
            if isinstance(state, dict):
                state.setdefault("data", {})["error"] = f"Search-only step failed: {str(e)}"
            else:
                state.data["error"] = f"Search-only step failed: {str(e)}"
            return state

    async def _advanced_rag_step(self, state: NodeState) -> NodeState:
        """Execute advanced RAG workflow"""
        try:
            # Convert dict to NodeState if needed
            if isinstance(state, dict):
                node_state = NodeState(**state)
            else:
                node_state = state
                
            result = await self.advanced_rag_node.execute(node_state)
            result.data["execution_steps"].append("advanced_rag")
            
            # Return as dict if input was dict
            if isinstance(state, dict):
                return result.model_dump()
            return result
        except Exception as e:
            if isinstance(state, dict):
                state.setdefault("data", {})["error"] = f"Advanced RAG step failed: {str(e)}"
            else:
                state.data["error"] = f"Advanced RAG step failed: {str(e)}"
            return state

    async def _simple_rag_step(self, state: NodeState) -> NodeState:
        """Execute simple RAG workflow (using basic search + generation)"""
        try:
            # Convert dict to NodeState if needed
            if isinstance(state, dict):
                node_state = NodeState(**state)
            else:
                node_state = state
                
            # Step 1: Perform search
            search_result = await self.search_node.execute(node_state)

            # If search failed, return error
            if "error" in search_result.data:
                search_result.data["execution_steps"].append("simple_rag")
                if isinstance(state, dict):
                    return search_result.model_dump()
                return search_result

            # Step 2: Extract search results and query
            query = search_result.data.get("query", "")
            search_results = search_result.data.get("search_results", [])
            
            # If no search results, return a message
            if not search_results:
                search_result.data["rag_answer"] = f"申し訳ございません。「{query}」に関する情報が見つかりませんでした。"
                search_result.data["retrieved_documents"] = []
                search_result.data["execution_steps"].append("simple_rag")
                if isinstance(state, dict):
                    return search_result.model_dump()
                return search_result

            # Step 3: Build context from search results
            context = self._build_context_from_results(search_results)
            
            # Step 4: Create prompt
            prompt = self._create_rag_prompt(query, context)
            
            # Step 5: Generate answer with LLM
            llm_state = NodeState()
            llm_state.messages = [prompt]
            llm_result = await self.llm_node.execute(llm_state)
            
            # Extract LLM response
            ai_response = llm_result.data.get("llm_response", "回答を生成できませんでした。")
            
            # Step 6: Update state with results
            search_result.data["rag_answer"] = ai_response
            search_result.data["retrieved_documents"] = search_results
            search_result.data["context_stats"] = {
                "documents_used": len(search_results),
                "total_characters": len(context)
            }
            search_result.data["execution_steps"].append("simple_rag")
            
            # Return as dict if input was dict
            if isinstance(state, dict):
                return search_result.model_dump()
            return search_result
            
        except Exception as e:
            if isinstance(state, dict):
                state.setdefault("data", {})["error"] = f"Simple RAG step failed: {str(e)}"
            else:
                state.data["error"] = f"Simple RAG step failed: {str(e)}"
            return state
    
    def _build_context_from_results(self, search_results: List[Dict[str, Any]]) -> str:
        """Build context string from search results"""
        context_parts = []
        for i, result in enumerate(search_results, 1):
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            score = result.get("score", 0)
            
            # Add document with metadata
            doc_info = f"【文書{i}】"
            if metadata.get("title"):
                doc_info += f" タイトル: {metadata['title']}"
            if metadata.get("source"):
                doc_info += f" | 出典: {metadata['source']}"
            doc_info += f" (関連度: {score:.2f})"
            
            context_parts.append(f"{doc_info}\n{content}")
        
        return "\n\n".join(context_parts)
    
    def _create_rag_prompt(self, query: str, context: str) -> str:
        """Create RAG prompt for LLM"""
        prompt = f"""以下の文脈情報を参考にして、質問に正確に答えてください。

文脈情報:
{context}

質問: {query}

回答の際は以下の点に注意してください：
- 文脈情報に基づいて正確に回答してください
- 情報が不足している場合は、その旨を明記してください
- 日本語で分かりやすく回答してください

回答:"""
        return prompt

    async def _finalize_response(self, state: NodeState) -> NodeState:
        """Finalize the workflow response"""
        # Handle both dict and NodeState
        if isinstance(state, dict):
            state_data = state.setdefault("data", {})
            state_metadata = state.setdefault("metadata", {})
        else:
            state_data = state.data
            state_metadata = state.metadata
            
        state_data.setdefault("execution_steps", []).append("finalize_response")

        # Ensure consistent output format
        if "rag_answer" not in state_data:
            state_data["rag_answer"] = "No answer generated"

        if "retrieved_documents" not in state_data:
            state_data["retrieved_documents"] = []

        if "context_stats" not in state_data:
            state_data["context_stats"] = {}

        state_metadata["workflow_completed"] = True
        return state

    async def run(self, input_data: RAGWorkflowInput) -> RAGWorkflowOutput:
        """Run the RAG workflow"""
        try:
            # Initialize state
            initial_state = NodeState()
            initial_state.data = {
                "query": input_data.query,
                "collection_name": input_data.collection_name,
                "search_type": input_data.search_type,
                "top_k": input_data.top_k,
                "include_conversation": input_data.include_conversation,
                "context_optimization": input_data.context_optimization,
                "workflow_type": input_data.workflow_type
            }

            # Run the graph - ainvoke returns a dict, not NodeState
            result = await self.graph.ainvoke(initial_state)
            
            # Extract data from result (result is a dict representation of NodeState)
            result_data = result.get("data", {}) if isinstance(result, dict) else result.data

            # Handle errors
            if "error" in result_data:
                return RAGWorkflowOutput(
                    workflow_type=input_data.workflow_type,
                    execution_steps=result_data.get("execution_steps", []),
                    success=False,
                    error_message=result_data["error"]
                )

            # Extract results
            return RAGWorkflowOutput(
                answer=result_data.get("rag_answer", ""),
                retrieved_documents=result_data.get("retrieved_documents", []),
                workflow_type=input_data.workflow_type,
                execution_steps=result_data.get("execution_steps", []),
                context_stats=result_data.get("context_stats", {}),
                success=True
            )

        except Exception as e:
            return RAGWorkflowOutput(
                workflow_type=input_data.workflow_type,
                execution_steps=["error"],
                success=False,
                error_message=str(e)
            )

    def get_mermaid_diagram(self) -> str:
        """Get Mermaid diagram representation of the RAG workflow"""
        return """
graph TD
    A[Start: User Query] --> B[Route Workflow]
    B --> C{Workflow Type?}

    C -->|search_only| D[Search Only Node]
    C -->|advanced_rag| E[Advanced RAG Node]
    C -->|simple_rag| F[Simple RAG Node]

    D --> G[Finalize Response]
    E --> G
    F --> G

    G --> H[End: RAG Response]

    subgraph "Search Only Path"
        D1[Query Processing]
        D2[Multi-Strategy Search]
        D3[Result Ranking]
        D --> D1 --> D2 --> D3
    end

    subgraph "Advanced RAG Path"
        E1[Context Management]
        E2[Query Enhancement]
        E3[Optimized Retrieval]
        E4[Contextualized Generation]
        E --> E1 --> E2 --> E3 --> E4
    end

    subgraph "Simple RAG Path"
        F1[Basic Search]
        F2[Simple Generation]
        F --> F1 --> F2
    end

    classDef startEnd fill:#e1f5fe
    classDef decision fill:#fff3e0
    classDef rag fill:#f3e5f5
    classDef search fill:#e8f5e8

    class A,H startEnd
    class C decision
    class E,F rag
    class D search
        """