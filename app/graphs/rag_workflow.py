from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel

from app.nodes.base_node import NodeState
from app.nodes.rag.advanced_rag_node import AdvancedRAGNode
from app.nodes.rag.search_node import SearchNode
from app.nodes.rag.document_ingest_node import DocumentIngestNode


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
        workflow_type = state.data.get("workflow_type", "simple")
        state.data["execution_steps"] = ["route_workflow"]
        state.data["routed_to"] = workflow_type
        return state

    def _decide_next_step(self, state: NodeState) -> str:
        """Decide which workflow step to execute next"""
        return state.data.get("routed_to", "simple_rag")

    async def _search_only_step(self, state: NodeState) -> NodeState:
        """Execute search-only workflow"""
        try:
            result = await self.search_node.execute(state)
            result.data["execution_steps"].append("search_only")
            return result
        except Exception as e:
            state.data["error"] = f"Search-only step failed: {str(e)}"
            return state

    async def _advanced_rag_step(self, state: NodeState) -> NodeState:
        """Execute advanced RAG workflow"""
        try:
            result = await self.advanced_rag_node.execute(state)
            result.data["execution_steps"].append("advanced_rag")
            return result
        except Exception as e:
            state.data["error"] = f"Advanced RAG step failed: {str(e)}"
            return state

    async def _simple_rag_step(self, state: NodeState) -> NodeState:
        """Execute simple RAG workflow (using basic search + generation)"""
        try:
            # First perform search
            search_result = await self.search_node.execute(state)

            # If search succeeded, format as simple RAG response
            if "error" not in search_result.data:
                # Simple response generation (placeholder)
                query = search_result.data.get("query", "")
                search_result.data["rag_answer"] = f"Based on search results for '{query}', here is the information found."
                search_result.data["retrieved_documents"] = search_result.data.get("search_results", [])

            search_result.data["execution_steps"].append("simple_rag")
            return search_result
        except Exception as e:
            state.data["error"] = f"Simple RAG step failed: {str(e)}"
            return state

    async def _finalize_response(self, state: NodeState) -> NodeState:
        """Finalize the workflow response"""
        state.data["execution_steps"].append("finalize_response")

        # Ensure consistent output format
        if "rag_answer" not in state.data:
            state.data["rag_answer"] = "No answer generated"

        if "retrieved_documents" not in state.data:
            state.data["retrieved_documents"] = []

        if "context_stats" not in state.data:
            state.data["context_stats"] = {}

        state.metadata["workflow_completed"] = True
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

            # Run the graph
            result = await self.graph.ainvoke(initial_state)

            # Handle errors
            if "error" in result.data:
                return RAGWorkflowOutput(
                    workflow_type=input_data.workflow_type,
                    execution_steps=result.data.get("execution_steps", []),
                    success=False,
                    error_message=result.data["error"]
                )

            # Extract results
            return RAGWorkflowOutput(
                answer=result.data.get("rag_answer", ""),
                retrieved_documents=result.data.get("retrieved_documents", []),
                workflow_type=input_data.workflow_type,
                execution_steps=result.data.get("execution_steps", []),
                context_stats=result.data.get("context_stats", {}),
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