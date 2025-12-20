"""
Resource models for RBAC Policy Engine.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ResourceAction(BaseModel):
    """Represents an action that can be performed on a resource."""
    
    name: str = Field(..., description="Action name (e.g., 'read', 'write')")
    description: Optional[str] = Field(None, description="Human-readable description")
    requires_ownership: bool = Field(False, description="Whether action requires resource ownership")


class Resource(BaseModel):
    """Represents a resource type that can be accessed."""
    
    name: str = Field(..., description="Resource name (e.g., 'invoice', 'user_profile')")
    description: Optional[str] = Field(None, description="Human-readable description")
    supported_actions: List[str] = Field(default_factory=list, description="Actions that can be performed")
    attributes: Dict[str, str] = Field(default_factory=dict, description="Resource attributes and their types")
    
    class Config:
        frozen = True
    
    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, other):
        if isinstance(other, Resource):
            return self.name == other.name
        return False


class ResourceSchema(BaseModel):
    """Schema defining all available resources and their properties."""
    
    resources: List[Resource]
    global_actions: List[str] = Field(
        default_factory=lambda: ["read", "write", "delete", "create", "list"],
        description="Actions available on all resources"
    )
