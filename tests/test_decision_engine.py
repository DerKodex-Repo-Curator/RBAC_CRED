"""
Tests for Decision Engine.
"""

import pytest
from src.core.decision_engine import DecisionEngine
from src.models.policy import (
    Policy, PolicyRule, PolicyCondition, ConditionGroup,
    Decision, LogicalOperator, ComparisonOperator
)


class TestDecisionEngine:
    """Tests for DecisionEngine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.policy = Policy(
            name="Test Policy",
            rules=[
                PolicyRule(
                    name="Admin Full Access",
                    roles=["admin"],
                    resources=[],
                    permissions=[],
                    effect=Decision.ALLOW,
                    priority=10
                ),
                PolicyRule(
                    name="Viewer Read Only",
                    roles=["viewer"],
                    resources=["invoice", "report"],
                    permissions=["read", "list"],
                    effect=Decision.ALLOW,
                    priority=50
                ),
                PolicyRule(
                    name="Block Guest Delete",
                    roles=["guest"],
                    resources=[],
                    permissions=["delete"],
                    effect=Decision.DENY,
                    priority=5
                ),
            ],
            default_decision=Decision.DENY
        )
        
        self.engine = DecisionEngine(self.policy)
    
    def test_admin_allow_all(self):
        """Test admin gets access to everything."""
        result = self.engine.evaluate(
            role="admin",
            resource="invoice",
            permission="delete"
        )
        
        assert result.decision == Decision.ALLOW
        assert result.matched_rule_name == "Admin Full Access"
    
    def test_viewer_read_allowed(self):
        """Test viewer can read invoices."""
        result = self.engine.evaluate(
            role="viewer",
            resource="invoice",
            permission="read"
        )
        
        assert result.decision == Decision.ALLOW
        assert result.matched_rule_name == "Viewer Read Only"
    
    def test_viewer_write_denied(self):
        """Test viewer cannot write (no matching rule)."""
        result = self.engine.evaluate(
            role="viewer",
            resource="invoice",
            permission="write"
        )
        
        assert result.decision == Decision.DENY
        assert result.matched_rule is None  # Default decision
    
    def test_guest_delete_denied(self):
        """Test guest delete is explicitly denied."""
        result = self.engine.evaluate(
            role="guest",
            resource="invoice",
            permission="delete"
        )
        
        assert result.decision == Decision.DENY
        assert result.matched_rule_name == "Block Guest Delete"
    
    def test_unknown_role_default_deny(self):
        """Test unknown role gets default deny."""
        result = self.engine.evaluate(
            role="unknown_role",
            resource="invoice",
            permission="read"
        )
        
        assert result.decision == Decision.DENY
        assert result.matched_rule is None
    
    def test_priority_ordering(self):
        """Test rules are evaluated by priority."""
        # Guest delete should match the Block Guest Delete rule (priority 5)
        # before any other rules
        result = self.engine.evaluate(
            role="guest",
            resource="invoice",
            permission="delete"
        )
        
        assert result.matched_rule_name == "Block Guest Delete"
    
    def test_condition_evaluation(self):
        """Test conditions are evaluated."""
        # Create a policy with conditions
        condition = PolicyCondition(
            attribute="environment",
            operator=ComparisonOperator.EQUALS,
            value="production"
        )
        
        policy = Policy(
            name="Conditional Policy",
            rules=[
                PolicyRule(
                    name="Production Only",
                    roles=["operator"],
                    resources=["configuration"],
                    permissions=["write"],
                    effect=Decision.ALLOW,
                    conditions=ConditionGroup(
                        operator=LogicalOperator.AND,
                        conditions=[condition]
                    )
                )
            ],
            default_decision=Decision.DENY
        )
        
        engine = DecisionEngine(policy)
        
        # Should allow in production
        result = engine.evaluate(
            role="operator",
            resource="configuration",
            permission="write",
            context={"environment": "production"}
        )
        assert result.decision == Decision.ALLOW
        
        # Should deny in staging
        result = engine.evaluate(
            role="operator",
            resource="configuration",
            permission="write",
            context={"environment": "staging"}
        )
        assert result.decision == Decision.DENY
    
    def test_and_conditions(self):
        """Test AND condition groups."""
        conditions = ConditionGroup(
            operator=LogicalOperator.AND,
            conditions=[
                PolicyCondition(
                    attribute="environment",
                    operator=ComparisonOperator.EQUALS,
                    value="production"
                ),
                PolicyCondition(
                    attribute="mfa_verified",
                    operator=ComparisonOperator.EQUALS,
                    value=True
                )
            ]
        )
        
        policy = Policy(
            name="AND Condition Policy",
            rules=[
                PolicyRule(
                    name="MFA + Production",
                    roles=["operator"],
                    resources=["configuration"],
                    permissions=["write"],
                    effect=Decision.ALLOW,
                    conditions=conditions
                )
            ],
            default_decision=Decision.DENY
        )
        
        engine = DecisionEngine(policy)
        
        # Both conditions met - should allow
        result = engine.evaluate(
            role="operator",
            resource="configuration",
            permission="write",
            context={"environment": "production", "mfa_verified": True}
        )
        assert result.decision == Decision.ALLOW
        
        # Only one condition met - should deny
        result = engine.evaluate(
            role="operator",
            resource="configuration",
            permission="write",
            context={"environment": "production", "mfa_verified": False}
        )
        assert result.decision == Decision.DENY
    
    def test_or_conditions(self):
        """Test OR condition groups."""
        conditions = ConditionGroup(
            operator=LogicalOperator.OR,
            conditions=[
                PolicyCondition(
                    attribute="environment",
                    operator=ComparisonOperator.EQUALS,
                    value="staging"
                ),
                PolicyCondition(
                    attribute="environment",
                    operator=ComparisonOperator.EQUALS,
                    value="development"
                )
            ]
        )
        
        policy = Policy(
            name="OR Condition Policy",
            rules=[
                PolicyRule(
                    name="Non-Prod Access",
                    roles=["developer"],
                    resources=["configuration"],
                    permissions=["write"],
                    effect=Decision.ALLOW,
                    conditions=conditions
                )
            ],
            default_decision=Decision.DENY
        )
        
        engine = DecisionEngine(policy)
        
        # Staging - should allow
        result = engine.evaluate(
            role="developer",
            resource="configuration",
            permission="write",
            context={"environment": "staging"}
        )
        assert result.decision == Decision.ALLOW
        
        # Development - should allow
        result = engine.evaluate(
            role="developer",
            resource="configuration",
            permission="write",
            context={"environment": "development"}
        )
        assert result.decision == Decision.ALLOW
        
        # Production - should deny
        result = engine.evaluate(
            role="developer",
            resource="configuration",
            permission="write",
            context={"environment": "production"}
        )
        assert result.decision == Decision.DENY
    
    def test_explain_decision(self):
        """Test detailed decision explanation."""
        explanation = self.engine.explain_decision(
            role="admin",
            resource="invoice",
            permission="delete"
        )
        
        assert explanation["decision"] == "ALLOW"
        assert explanation["matched_rule_name"] == "Admin Full Access"
        assert "policy_info" in explanation
        assert "request" in explanation
    
    def test_get_effective_permissions(self):
        """Test getting all effective permissions."""
        permissions = self.engine.get_effective_permissions(
            role="viewer",
            resource="invoice"
        )
        
        assert permissions["read"] == Decision.ALLOW
        assert permissions["list"] == Decision.ALLOW
        assert permissions["write"] == Decision.DENY
        assert permissions["delete"] == Decision.DENY
    
    def test_no_policy(self):
        """Test engine with no policy returns deny."""
        engine = DecisionEngine()
        
        result = engine.evaluate(
            role="admin",
            resource="invoice",
            permission="read"
        )
        
        assert result.decision == Decision.DENY
        assert "No policy configured" in result.reason
