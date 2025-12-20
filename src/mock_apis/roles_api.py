"""
Mock Roles & Permissions Discovery API.
Lists valid roles and permissions dynamically.
"""

from typing import List, Dict, Optional
from src.models.role import Role, Permission, RolePermissionMapping


class RolesPermissionsAPI:
    """
    Mock API for discovering available roles and permissions.
    In a real system, this would connect to an IAM service.
    """
    
    def __init__(self):
        # Simulated database of roles
        self._roles: Dict[str, Role] = {
            "admin": Role(
                name="admin",
                description="Full system administrator with all permissions",
                parent_roles=[]
            ),
            "operator": Role(
                name="operator",
                description="Operational user who can manage resources",
                parent_roles=["viewer"]
            ),
            "viewer": Role(
                name="viewer",
                description="Read-only access to resources",
                parent_roles=[]
            ),
            "auditor": Role(
                name="auditor",
                description="Can view and audit all activities",
                parent_roles=["viewer"]
            ),
            "developer": Role(
                name="developer",
                description="Can manage development resources",
                parent_roles=["viewer"]
            ),
            "analyst": Role(
                name="analyst",
                description="Can view and analyze data",
                parent_roles=["viewer"]
            ),
            "manager": Role(
                name="manager",
                description="Can manage team resources and approve requests",
                parent_roles=["operator"]
            ),
            "guest": Role(
                name="guest",
                description="Limited temporary access",
                parent_roles=[]
            ),
        }
        
        # Simulated database of permissions
        self._permissions: Dict[str, Permission] = {
            "read": Permission(name="read", description="View resource content"),
            "write": Permission(name="write", description="Modify resource content"),
            "delete": Permission(name="delete", description="Remove resources"),
            "create": Permission(name="create", description="Create new resources"),
            "list": Permission(name="list", description="List resources"),
            "export": Permission(name="export", description="Export resource data"),
            "import": Permission(name="import", description="Import resource data"),
            "approve": Permission(name="approve", description="Approve pending actions"),
            "reject": Permission(name="reject", description="Reject pending actions"),
            "execute": Permission(name="execute", description="Execute operations"),
            "configure": Permission(name="configure", description="Configure settings"),
            "audit": Permission(name="audit", description="Audit activities"),
        }
        
        # Default role-permission mappings
        self._default_mappings: List[RolePermissionMapping] = [
            RolePermissionMapping(
                role="admin",
                permissions=["read", "write", "delete", "create", "list", "export", "import", "approve", "reject", "execute", "configure", "audit"]
            ),
            RolePermissionMapping(
                role="operator",
                permissions=["read", "write", "create", "list", "execute"]
            ),
            RolePermissionMapping(
                role="viewer",
                permissions=["read", "list"]
            ),
            RolePermissionMapping(
                role="auditor",
                permissions=["read", "list", "audit", "export"]
            ),
            RolePermissionMapping(
                role="developer",
                permissions=["read", "write", "create", "list", "execute", "configure"]
            ),
            RolePermissionMapping(
                role="analyst",
                permissions=["read", "list", "export"]
            ),
            RolePermissionMapping(
                role="manager",
                permissions=["read", "write", "create", "list", "approve", "reject"]
            ),
            RolePermissionMapping(
                role="guest",
                permissions=["read"]
            ),
        ]
    
    def get_all_roles(self) -> List[Role]:
        """Get all available roles."""
        return list(self._roles.values())
    
    def get_role(self, name: str) -> Optional[Role]:
        """Get a specific role by name."""
        return self._roles.get(name.lower())
    
    def get_all_permissions(self) -> List[Permission]:
        """Get all available permissions."""
        return list(self._permissions.values())
    
    def get_permission(self, name: str) -> Optional[Permission]:
        """Get a specific permission by name."""
        return self._permissions.get(name.lower())
    
    def get_role_names(self) -> List[str]:
        """Get all role names."""
        return list(self._roles.keys())
    
    def get_permission_names(self) -> List[str]:
        """Get all permission names."""
        return list(self._permissions.keys())
    
    def is_valid_role(self, name: str) -> bool:
        """Check if a role name is valid."""
        return name.lower() in self._roles
    
    def is_valid_permission(self, name: str) -> bool:
        """Check if a permission name is valid."""
        return name.lower() in self._permissions
    
    def get_default_permissions_for_role(self, role_name: str) -> List[str]:
        """Get default permissions for a role."""
        for mapping in self._default_mappings:
            if mapping.role == role_name.lower():
                return mapping.permissions
        return []
    
    def get_role_hierarchy(self, role_name: str) -> List[str]:
        """Get the role hierarchy (including parent roles)."""
        role = self.get_role(role_name)
        if not role:
            return []
        
        hierarchy = [role.name]
        for parent_name in role.parent_roles:
            parent_hierarchy = self.get_role_hierarchy(parent_name)
            hierarchy.extend(parent_hierarchy)
        
        return list(set(hierarchy))
    
    def discover(self) -> Dict:
        """
        Discovery endpoint - returns all roles and permissions.
        This is the main API endpoint that would be called for discovery.
        """
        return {
            "roles": [role.model_dump() for role in self.get_all_roles()],
            "permissions": [perm.model_dump() for perm in self.get_all_permissions()],
            "default_mappings": [mapping.model_dump() for mapping in self._default_mappings],
        }
