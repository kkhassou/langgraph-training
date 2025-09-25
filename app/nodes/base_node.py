from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class NodeState(BaseModel):
    """Base state model for node communication"""
    messages: list = []
    data: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}


class BaseNode(ABC):
    """Base class for all LangGraph nodes"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, state: NodeState) -> NodeState:
        """Execute the node logic"""
        pass

    def get_info(self) -> Dict[str, str]:
        """Get node information"""
        return {
            "name": self.name,
            "description": self.description,
            "type": self.__class__.__name__
        }

    def __str__(self) -> str:
        return f"{self.name} ({self.__class__.__name__})"


class NodeInput(BaseModel):
    """Base input model for nodes"""
    input_text: Optional[str] = None
    parameters: Dict[str, Any] = {}


class NodeOutput(BaseModel):
    """Base output model for nodes"""
    output_text: str
    data: Dict[str, Any] = {}
    success: bool = True
    error_message: Optional[str] = None