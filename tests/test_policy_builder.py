"""
Tests for Policy Builder.
"""

import pytest
from src.core.policy_builder import PolicyBuilder
from src.models.policy import Decision, LogicalOperator, ComparisonOperator


class TestPolicyBuilder:
    """Tests for PolicyBuilder."""
    
    def setup_method(self):
        self.builder = PolicyBuilder()
    
    def test_create_policy(self):
        """Test creating a new policy."""
        policy = self.builder.create_policy(
            name="Test Policy",
            description="A test policy"
        )
        
        assert policy is not None
        assert policy.name == "Test Policy"
        assert policy.description == "A test policy"
        assert len(policy.rules) == 0
    
    def test_add_valid_rule(self):
        """Test adding a valid rule."""
        self.builder.create_policy()
        
        success, message, rule = self.builder.add_rule(
            name="Admin Read Invoices",
            roles=["admin"],
            resources=["invoice"],
            permissions=["read"],
            effect=Decision.ALLOW
        )
        
        assert success is True
        assert rule is not None
        assert rule.name == "Admin Read Invoices"
    
    def test_add_rule_invalid_role(self):
        """Test adding a rule with invalid role."""
        self.builder.create_policy()
        
        success, message, rule = self.builder.add_rule(
            name="Bad Rule",
            roles=["nonexistent_role"],
            resources=["invoice"],
            permissions=["read"],
            effect=Decision.ALLOW
        )
        
        assert success is False
        assert "Unknown role" in message
        assert rule is None
    
    def test_add_rule_invalid_resource(self):
        """Test adding a rule with invalid resource."""
        self.builder.create_policy()
        
        success, message, rule = self.builder.add_rule(
            name="Bad Rule",
            roles=["admin"],
            resources=["nonexistent_resource"],
            permissions=["read"],
            effect=Decision.ALLOW
        )
        
        assert success is False
        assert "Unknown resource" in message
    
    def test_add_rule_invalid_permission(self):
        """Test adding a rule with invalid permission."""
        self.builder.create_policy()
        
        success, message, rule = self.builder.add_rule(
            name="Bad Rule",
            roles=["admin"],
            resources=["invoice"],
            permissions=["nonexistent_permission"],
            effect=Decision.ALLOW
        )
        
        assert success is False
        assert "Unknown permission" in message
    
    def test_add_rule_unsupported_action(self):
        """Test adding a rule with unsupported action for resource."""
        self.builder.create_policy()
        
        success, message, rule = self.builder.add_rule(
            name="Bad Rule",
            roles=["admin"],
            resources=["audit_log"],  # audit_log doesn't support delete
            permissions=["delete"],
            effect=Decision.ALLOW
        )
        
        assert success is False
        assert "not supported" in message
    
    def test_create_condition(self):
        """Test creating a condition."""
        success, message, condition = self.builder.create_condition(
            attribute="environment",
            operator="equals",
            value="production"
        )
        
        assert success is True
        assert condition is not None
        assert condition.attribute == "environment"
        assert condition.value == "production"
    
    def test_create_condition_invalid_attribute(self):
        """Test creating a condition with invalid attribute."""
        success, message, condition = self.builder.create_condition(
            attribute="nonexistent_attr",
            operator="equals",
            value="test"
        )
        
        assert success is False
        assert condition is None
    
    def test_create_condition_invalid_value(self):
        """Test creating a condition with invalid value for enum."""
        success, message, condition = self.builder.create_condition(
            attribute="environment",
            operator="equals",
            value="invalid_environment"
        )
        
        assert success is False
        assert condition is None
    
    def test_remove_rule(self):
        """Test removing a rule."""
        self.builder.create_policy()
        
        success, message, rule = self.builder.add_rule(
            name="To Remove",
            roles=["admin"],
            resources=["invoice"],
            permissions=["read"],
            effect=Decision.ALLOW
        )
        
        assert success is True
        rule_id = rule.id
        
        success, message = self.builder.remove_rule(rule_id)
        assert success is True
        
        policy = self.builder.get_policy()
        assert len(policy.rules) == 0
    
    def test_validate_policy(self):
        """Test policy validation."""
        self.builder.create_policy()
        
        self.builder.add_rule(
            name="Valid Rule",
            roles=["admin"],
            resources=["invoice"],
            permissions=["read"],
            effect=Decision.ALLOW
        )
        
        is_valid, report = self.builder.validate_policy()
        assert is_valid is True
    
    def test_export_policy(self):
        """Test exporting policy as dict."""
        self.builder.create_policy(name="Export Test")
        
        self.builder.add_rule(
            name="Test Rule",
            roles=["admin"],
            resources=["invoice"],
            permissions=["read"],
            effect=Decision.ALLOW
        )
        
        policy_dict = self.builder.export_policy()
        
        assert policy_dict is not None
        assert policy_dict["name"] == "Export Test"
        assert len(policy_dict["rules"]) == 1
    
    def test_get_available_resources(self):
        """Test getting available resources."""
        resources = self.builder.get_available_resources()
        
        assert "invoice" in resources
        assert "user_profile" in resources
        assert "report" in resources
    
    def test_get_available_roles(self):
        """Test getting available roles."""
        roles = self.builder.get_available_roles()
        
        assert "admin" in roles
        assert "viewer" in roles
        assert "operator" in roles
    
    def test_get_resource_actions(self):
        """Test getting actions for a resource."""
        actions = self.builder.get_resource_actions("invoice")
        
        assert "read" in actions
        assert "write" in actions
