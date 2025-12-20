"""
Context attribute models for RBAC Policy Engine.
"""

from typing import List, Optional, Any, Dict, Union
from pydantic import BaseModel, Field
from enum import Enum


class AttributeType(str, Enum):
    """Data types for context attributes."""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    FLOAT = "float"
    LIST = "list"
    DATETIME = "datetime"
    ENUM = "enum"


class ContextAttribute(BaseModel):
    """Represents a contextual attribute that can be used in policy conditions."""
    
    name: str = Field(..., description="Attribute name (e.g., 'environment', 'time_of_day')")
    type: AttributeType = Field(..., description="Data type of the attribute")
    description: Optional[str] = Field(None, description="Human-readable description")
    allowed_values: Optional[List[Any]] = Field(None, description="Allowed values for enum types")
    default_value: Optional[Any] = Field(None, description="Default value if not provided")
    
    class Config:
        frozen = True
    
    def __hash__(self):
        return hash(self.name)


class ContextSchema(BaseModel):
    """Schema defining all available context attributes."""
    
    attributes: List[ContextAttribute]
    
    def get_attribute(self, name: str) -> Optional[ContextAttribute]:
        """Get attribute by name."""
        for attr in self.attributes:
            if attr.name == name:
                return attr
        return None
    
    def get_attribute_names(self) -> List[str]:
        """Get all attribute names."""
        return [attr.name for attr in self.attributes]


class ContextValue(BaseModel):
    """A specific context value for policy evaluation."""
    
    attribute: str = Field(..., description="Name of the context attribute")
    value: Any = Field(..., description="Value of the attribute")
