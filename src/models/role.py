"""
Role and Permission models for RBAC Policy Engine.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class Permission(BaseModel):
    """Represents a permission/action that can be performed."""
    
    name: str = Field(..., description="Permission name (e.g., 'read', 'write', 'delete')")
    description: Optional[str] = Field(None, description="Human-readable description")
    
    class Config:
        frozen = True
    
    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, other):
        if isinstance(other, Permission):
            return self.name == other.name
        return False


class Role(BaseModel):
    """Represents a role that can be assigned to users."""
    
    name: str = Field(..., description="Role name (e.g., 'admin', 'operator', 'viewer')")
    description: Optional[str] = Field(None, description="Human-readable description")
    parent_roles: List[str] = Field(default_factory=list, description="Inherited roles")
    
    class Config:
        frozen = True
    
    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, other):
        if isinstance(other, Role):
            return self.name == other.name
        return False


class RolePermissionMapping(BaseModel):
    """Maps roles to their default permissions."""
    
    role: str
    permissions: List[str]
    resources: List[str] = Field(default_factory=list, description="Resources this mapping applies to")
