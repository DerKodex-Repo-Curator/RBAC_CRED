"""
Policy models for RBAC Policy Engine.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from datetime import datetime
import uuid


class Decision(str, Enum):
    """Final policy decision."""
    ALLOW = "ALLOW"
    DENY = "DENY"


class LogicalOperator(str, Enum):
    """Logical operators for combining conditions."""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class ComparisonOperator(str, Enum):
    """Comparison operators for conditions."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    IN = "in"
    NOT_IN = "not_in"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_OR_EQUALS = "greater_than_or_equals"
    LESS_THAN_OR_EQUALS = "less_than_or_equals"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"


class PolicyCondition(BaseModel):
    """A condition that must be met for a policy rule to apply."""
    
    attribute: str = Field(..., description="Context attribute name")
    operator: ComparisonOperator = Field(..., description="Comparison operator")
    value: Any = Field(..., description="Value to compare against")
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate this condition against a context."""
        if self.attribute not in context:
            return False
        
        actual_value = context[self.attribute]
        
        if self.operator == ComparisonOperator.EQUALS:
            return actual_value == self.value
        elif self.operator == ComparisonOperator.NOT_EQUALS:
            return actual_value != self.value
        elif self.operator == ComparisonOperator.IN:
            return actual_value in self.value
        elif self.operator == ComparisonOperator.NOT_IN:
            return actual_value not in self.value
        elif self.operator == ComparisonOperator.GREATER_THAN:
            return actual_value > self.value
        elif self.operator == ComparisonOperator.LESS_THAN:
            return actual_value < self.value
        elif self.operator == ComparisonOperator.GREATER_THAN_OR_EQUALS:
            return actual_value >= self.value
        elif self.operator == ComparisonOperator.LESS_THAN_OR_EQUALS:
            return actual_value <= self.value
        elif self.operator == ComparisonOperator.CONTAINS:
            return self.value in actual_value
        elif self.operator == ComparisonOperator.STARTS_WITH:
            return str(actual_value).startswith(str(self.value))
        elif self.operator == ComparisonOperator.ENDS_WITH:
            return str(actual_value).endswith(str(self.value))
        
        return False


class ConditionGroup(BaseModel):
    """A group of conditions combined with a logical operator."""
    
    operator: LogicalOperator = Field(LogicalOperator.AND, description="Logical operator")
    conditions: List[Union[PolicyCondition, "ConditionGroup"]] = Field(
        default_factory=list, 
        description="List of conditions or nested condition groups"
    )
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate this condition group against a context."""
        if not self.conditions:
            return True
        
        results = []
        for condition in self.conditions:
            if isinstance(condition, PolicyCondition):
                results.append(condition.evaluate(context))
            elif isinstance(condition, ConditionGroup):
                results.append(condition.evaluate(context))
        
        if self.operator == LogicalOperator.AND:
            return all(results)
        elif self.operator == LogicalOperator.OR:
            return any(results)
        elif self.operator == LogicalOperator.NOT:
            # NOT applies to the first condition only
            return not results[0] if results else True
        
        return False


class PolicyRule(BaseModel):
    """A single rule within a policy."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8], description="Unique rule ID")
    name: str = Field(..., description="Human-readable rule name")
    description: Optional[str] = Field(None, description="Rule description")
    
    # Rule matching criteria
    roles: List[str] = Field(default_factory=list, description="Roles this rule applies to")
    resources: List[str] = Field(default_factory=list, description="Resources this rule applies to")
    permissions: List[str] = Field(default_factory=list, description="Permissions this rule grants/denies")
    
    # Conditions
    conditions: Optional[ConditionGroup] = Field(None, description="Conditions for this rule")
    
    # Decision
    effect: Decision = Field(Decision.ALLOW, description="Effect when rule matches")
    
    # Priority (lower = higher priority)
    priority: int = Field(100, description="Rule priority (lower = higher priority)")
    
    def matches(self, role: str, resource: str, permission: str, context: Dict[str, Any]) -> bool:
        """Check if this rule matches the given request."""
        # Check role
        if self.roles and role not in self.roles:
            return False
        
        # Check resource
        if self.resources and resource not in self.resources:
            return False
        
        # Check permission
        if self.permissions and permission not in self.permissions:
            return False
        
        # Check conditions
        if self.conditions and not self.conditions.evaluate(context):
            return False
        
        return True


class Policy(BaseModel):
    """Complete RBAC policy definition."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique policy ID")
    name: str = Field("RBAC Policy", description="Policy name")
    version: str = Field("1.0.0", description="Policy version")
    description: Optional[str] = Field(None, description="Policy description")
    
    # Policy rules
    rules: List[PolicyRule] = Field(default_factory=list, description="Policy rules")
    
    # Default decision when no rules match
    default_decision: Decision = Field(Decision.DENY, description="Default decision when no rules match")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(None, description="User who created the policy")
    
    def add_rule(self, rule: PolicyRule) -> None:
        """Add a rule to the policy."""
        self.rules.append(rule)
        self.updated_at = datetime.utcnow()
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID."""
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                self.rules.pop(i)
                self.updated_at = datetime.utcnow()
                return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[PolicyRule]:
        """Get a rule by ID."""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None
    
    def to_json(self) -> Dict[str, Any]:
        """Export policy as JSON-serializable dict."""
        return self.model_dump(mode="json")


class PolicyEvaluationRequest(BaseModel):
    """Request to evaluate a policy decision."""
    
    role: str = Field(..., description="Role of the user")
    resource: str = Field(..., description="Resource being accessed")
    permission: str = Field(..., description="Permission/action being requested")
    context: Dict[str, Any] = Field(default_factory=dict, description="Contextual attributes")


class PolicyEvaluationResult(BaseModel):
    """Result of a policy evaluation."""
    
    decision: Decision = Field(..., description="Final decision")
    matched_rule: Optional[str] = Field(None, description="ID of the rule that matched")
    matched_rule_name: Optional[str] = Field(None, description="Name of the rule that matched")
    reason: str = Field(..., description="Explanation of the decision")
    evaluation_time_ms: float = Field(..., description="Time taken to evaluate in milliseconds")


# Update forward references
ConditionGroup.model_rebuild()
