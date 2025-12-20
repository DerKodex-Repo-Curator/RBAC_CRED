"""
Tests for Mock APIs.
"""

import pytest
from src.mock_apis import RolesPermissionsAPI, ResourceSchemaAPI, ContextSchemaAPI, PolicyValidatorAPI
from src.models.policy import Policy, PolicyRule, Decision


class TestRolesPermissionsAPI:
    """Tests for RolesPermissionsAPI."""
    
    def setup_method(self):
        self.api = RolesPermissionsAPI()
    
    def test_get_all_roles(self):
        """Test getting all roles."""
        roles = self.api.get_all_roles()
        assert len(roles) > 0
        assert any(r.name == "admin" for r in roles)
        assert any(r.name == "viewer" for r in roles)
    
    def test_get_role(self):
        """Test getting a specific role."""
        role = self.api.get_role("admin")
        assert role is not None
        assert role.name == "admin"
        
        role = self.api.get_role("nonexistent")
        assert role is None
    
    def test_get_all_permissions(self):
        """Test getting all permissions."""
        permissions = self.api.get_all_permissions()
        assert len(permissions) > 0
        assert any(p.name == "read" for p in permissions)
        assert any(p.name == "write" for p in permissions)
    
    def test_is_valid_role(self):
        """Test role validation."""
        assert self.api.is_valid_role("admin") is True
        assert self.api.is_valid_role("ADMIN") is True  # Case insensitive
        assert self.api.is_valid_role("invalid_role") is False
    
    def test_is_valid_permission(self):
        """Test permission validation."""
        assert self.api.is_valid_permission("read") is True
        assert self.api.is_valid_permission("invalid_perm") is False
    
    def test_get_default_permissions_for_role(self):
        """Test getting default permissions for a role."""
        perms = self.api.get_default_permissions_for_role("admin")
        assert "read" in perms
        assert "write" in perms
        assert "delete" in perms
        
        perms = self.api.get_default_permissions_for_role("viewer")
        assert "read" in perms
        assert "write" not in perms
    
    def test_discover(self):
        """Test the discovery endpoint."""
        data = self.api.discover()
        assert "roles" in data
        assert "permissions" in data
        assert "default_mappings" in data


class TestResourceSchemaAPI:
    """Tests for ResourceSchemaAPI."""
    
    def setup_method(self):
        self.api = ResourceSchemaAPI()
    
    def test_get_all_resources(self):
        """Test getting all resources."""
        resources = self.api.get_all_resources()
        assert len(resources) > 0
        assert any(r.name == "invoice" for r in resources)
    
    def test_get_resource(self):
        """Test getting a specific resource."""
        resource = self.api.get_resource("invoice")
        assert resource is not None
        assert resource.name == "invoice"
        assert len(resource.supported_actions) > 0
    
    def test_is_valid_resource(self):
        """Test resource validation."""
        assert self.api.is_valid_resource("invoice") is True
        assert self.api.is_valid_resource("invalid_resource") is False
    
    def test_get_supported_actions(self):
        """Test getting supported actions for a resource."""
        actions = self.api.get_supported_actions("invoice")
        assert "read" in actions
        assert "write" in actions
    
    def test_is_action_supported(self):
        """Test action support validation."""
        assert self.api.is_action_supported("invoice", "read") is True
        assert self.api.is_action_supported("audit_log", "delete") is False


class TestContextSchemaAPI:
    """Tests for ContextSchemaAPI."""
    
    def setup_method(self):
        self.api = ContextSchemaAPI()
    
    def test_get_all_attributes(self):
        """Test getting all context attributes."""
        attrs = self.api.get_all_attributes()
        assert len(attrs) > 0
        assert any(a.name == "environment" for a in attrs)
    
    def test_get_attribute(self):
        """Test getting a specific attribute."""
        attr = self.api.get_attribute("environment")
        assert attr is not None
        assert attr.name == "environment"
        assert attr.allowed_values is not None
    
    def test_validate_attribute_value(self):
        """Test attribute value validation."""
        # Valid enum value
        is_valid, msg = self.api.validate_attribute_value("environment", "production")
        assert is_valid is True
        
        # Invalid enum value
        is_valid, msg = self.api.validate_attribute_value("environment", "invalid_env")
        assert is_valid is False
        
        # Boolean attribute
        is_valid, msg = self.api.validate_attribute_value("mfa_verified", True)
        assert is_valid is True
        
        is_valid, msg = self.api.validate_attribute_value("mfa_verified", "not_a_bool")
        assert is_valid is False


class TestPolicyValidatorAPI:
    """Tests for PolicyValidatorAPI."""
    
    def setup_method(self):
        self.validator = PolicyValidatorAPI()
    
    def test_validate_valid_policy(self):
        """Test validating a valid policy."""
        policy = Policy(
            name="Test Policy",
            rules=[
                PolicyRule(
                    name="Admin Read",
                    roles=["admin"],
                    resources=["invoice"],
                    permissions=["read"],
                    effect=Decision.ALLOW
                )
            ]
        )
        
        result = self.validator.validate(policy)
        assert result.is_valid is True
    
    def test_validate_invalid_role(self):
        """Test validation catches invalid roles."""
        policy = Policy(
            name="Test Policy",
            rules=[
                PolicyRule(
                    name="Invalid Role Rule",
                    roles=["nonexistent_role"],
                    resources=["invoice"],
                    permissions=["read"],
                    effect=Decision.ALLOW
                )
            ]
        )
        
        result = self.validator.validate(policy)
        assert result.is_valid is False
        assert any(issue.code == "INVALID_ROLE" for issue in result.issues)
    
    def test_validate_invalid_resource(self):
        """Test validation catches invalid resources."""
        policy = Policy(
            name="Test Policy",
            rules=[
                PolicyRule(
                    name="Invalid Resource Rule",
                    roles=["admin"],
                    resources=["nonexistent_resource"],
                    permissions=["read"],
                    effect=Decision.ALLOW
                )
            ]
        )
        
        result = self.validator.validate(policy)
        assert result.is_valid is False
        assert any(issue.code == "INVALID_RESOURCE" for issue in result.issues)
    
    def test_validate_unsupported_action(self):
        """Test validation catches unsupported actions."""
        policy = Policy(
            name="Test Policy",
            rules=[
                PolicyRule(
                    name="Unsupported Action Rule",
                    roles=["admin"],
                    resources=["audit_log"],  # audit_log doesn't support delete
                    permissions=["delete"],
                    effect=Decision.ALLOW
                )
            ]
        )
        
        result = self.validator.validate(policy)
        assert result.is_valid is False
        assert any(issue.code == "UNSUPPORTED_ACTION" for issue in result.issues)
