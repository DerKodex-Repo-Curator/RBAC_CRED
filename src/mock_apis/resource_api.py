"""
Mock Resource Schema API.
Defines valid resource types and supported actions.
"""

from typing import List, Dict, Optional
from src.models.resource import Resource, ResourceAction, ResourceSchema


class ResourceSchemaAPI:
    """
    Mock API for discovering available resources and their supported actions.
    In a real system, this would connect to a resource registry.
    """
    
    def __init__(self):
        # Simulated database of resources
        self._resources: Dict[str, Resource] = {
            "invoice": Resource(
                name="invoice",
                description="Financial invoices for billing",
                supported_actions=["read", "write", "delete", "create", "list", "export", "approve"],
                attributes={
                    "amount": "float",
                    "status": "string",
                    "customer_id": "string",
                    "created_date": "datetime"
                }
            ),
            "user_profile": Resource(
                name="user_profile",
                description="User account profiles",
                supported_actions=["read", "write", "delete", "create", "list"],
                attributes={
                    "email": "string",
                    "role": "string",
                    "department": "string",
                    "active": "boolean"
                }
            ),
            "report": Resource(
                name="report",
                description="Analytics and business reports",
                supported_actions=["read", "create", "list", "export", "delete"],
                attributes={
                    "type": "string",
                    "generated_at": "datetime",
                    "format": "string"
                }
            ),
            "payment": Resource(
                name="payment",
                description="Payment transactions",
                supported_actions=["read", "create", "list", "approve", "reject"],
                attributes={
                    "amount": "float",
                    "currency": "string",
                    "status": "string",
                    "method": "string"
                }
            ),
            "order": Resource(
                name="order",
                description="Customer orders",
                supported_actions=["read", "write", "delete", "create", "list", "approve", "reject"],
                attributes={
                    "total": "float",
                    "status": "string",
                    "customer_id": "string",
                    "items_count": "integer"
                }
            ),
            "product": Resource(
                name="product",
                description="Product catalog items",
                supported_actions=["read", "write", "delete", "create", "list", "import", "export"],
                attributes={
                    "name": "string",
                    "price": "float",
                    "category": "string",
                    "stock": "integer"
                }
            ),
            "customer": Resource(
                name="customer",
                description="Customer accounts",
                supported_actions=["read", "write", "delete", "create", "list", "export"],
                attributes={
                    "name": "string",
                    "email": "string",
                    "tier": "string",
                    "lifetime_value": "float"
                }
            ),
            "audit_log": Resource(
                name="audit_log",
                description="System audit logs",
                supported_actions=["read", "list", "export", "audit"],
                attributes={
                    "action": "string",
                    "user_id": "string",
                    "timestamp": "datetime",
                    "resource": "string"
                }
            ),
            "configuration": Resource(
                name="configuration",
                description="System configuration settings",
                supported_actions=["read", "write", "configure"],
                attributes={
                    "key": "string",
                    "value": "string",
                    "category": "string"
                }
            ),
            "dashboard": Resource(
                name="dashboard",
                description="Analytics dashboards",
                supported_actions=["read", "write", "create", "delete", "list"],
                attributes={
                    "name": "string",
                    "owner": "string",
                    "shared": "boolean"
                }
            ),
        }
        
        # Global actions available on all resources
        self._global_actions: List[str] = ["read", "write", "delete", "create", "list"]
    
    def get_all_resources(self) -> List[Resource]:
        """Get all available resources."""
        return list(self._resources.values())
    
    def get_resource(self, name: str) -> Optional[Resource]:
        """Get a specific resource by name."""
        return self._resources.get(name.lower())
    
    def get_resource_names(self) -> List[str]:
        """Get all resource names."""
        return list(self._resources.keys())
    
    def is_valid_resource(self, name: str) -> bool:
        """Check if a resource name is valid."""
        return name.lower() in self._resources
    
    def get_supported_actions(self, resource_name: str) -> List[str]:
        """Get supported actions for a resource."""
        resource = self.get_resource(resource_name)
        if resource:
            return resource.supported_actions
        return []
    
    def is_action_supported(self, resource_name: str, action: str) -> bool:
        """Check if an action is supported for a resource."""
        supported_actions = self.get_supported_actions(resource_name)
        return action.lower() in supported_actions
    
    def get_resource_attributes(self, resource_name: str) -> Dict[str, str]:
        """Get attributes for a resource."""
        resource = self.get_resource(resource_name)
        if resource:
            return resource.attributes
        return {}
    
    def get_schema(self) -> ResourceSchema:
        """Get the complete resource schema."""
        return ResourceSchema(
            resources=self.get_all_resources(),
            global_actions=self._global_actions
        )
    
    def discover(self) -> Dict:
        """
        Discovery endpoint - returns all resources and their schemas.
        This is the main API endpoint that would be called for discovery.
        """
        return {
            "resources": [res.model_dump() for res in self.get_all_resources()],
            "global_actions": self._global_actions,
        }
