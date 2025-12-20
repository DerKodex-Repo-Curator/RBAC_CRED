"""
Mock Policy Validator API.
Validates policy structure, role names, permissions, attribute types, and logical correctness.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.models.policy import Policy, PolicyRule, PolicyCondition, ConditionGroup, LogicalOperator
from src.mock_apis.roles_api import RolesPermissionsAPI
from src.mock_apis.resource_api import ResourceSchemaAPI
from src.mock_apis.context_api import ContextSchemaAPI


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""
    severity: ValidationSeverity
    code: str
    message: str
    path: Optional[str] = None
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationResult:
    """Result of policy validation."""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    validated_at: str = ""
    policy_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid,
            "issues": [issue.to_dict() for issue in self.issues],
            "validated_at": self.validated_at,
            "policy_id": self.policy_id,
            "error_count": len([i for i in self.issues if i.severity == ValidationSeverity.ERROR]),
            "warning_count": len([i for i in self.issues if i.severity == ValidationSeverity.WARNING]),
        }


class PolicyValidatorAPI:
    """
    Mock API for validating RBAC policies.
    Validates structure, references, and logical correctness.
    """
    
    def __init__(
        self,
        roles_api: Optional[RolesPermissionsAPI] = None,
        resource_api: Optional[ResourceSchemaAPI] = None,
        context_api: Optional[ContextSchemaAPI] = None
    ):
        self.roles_api = roles_api or RolesPermissionsAPI()
        self.resource_api = resource_api or ResourceSchemaAPI()
        self.context_api = context_api or ContextSchemaAPI()
    
    def validate(self, policy: Policy) -> ValidationResult:
        """
        Validate a complete policy.
        Returns a ValidationResult with all issues found.
        """
        from datetime import datetime
        
        issues: List[ValidationIssue] = []
        
        # Validate policy structure
        issues.extend(self._validate_policy_structure(policy))
        
        # Validate each rule
        for i, rule in enumerate(policy.rules):
            rule_issues = self._validate_rule(rule, f"rules[{i}]")
            issues.extend(rule_issues)
        
        # Validate logical consistency
        issues.extend(self._validate_logical_consistency(policy))
        
        # Check for duplicate rules
        issues.extend(self._check_duplicate_rules(policy))
        
        # Determine if policy is valid (no errors)
        has_errors = any(issue.severity == ValidationSeverity.ERROR for issue in issues)
        
        return ValidationResult(
            is_valid=not has_errors,
            issues=issues,
            validated_at=datetime.utcnow().isoformat(),
            policy_id=policy.id
        )
    
    def _validate_policy_structure(self, policy: Policy) -> List[ValidationIssue]:
        """Validate basic policy structure."""
        issues = []
        
        if not policy.name or len(policy.name.strip()) == 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="POLICY_NAME_REQUIRED",
                message="Policy name is required",
                path="name",
                suggestion="Provide a descriptive name for the policy"
            ))
        
        if not policy.rules:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="NO_RULES_DEFINED",
                message="Policy has no rules defined",
                path="rules",
                suggestion="Add at least one rule to make the policy effective"
            ))
        
        return issues
    
    def _validate_rule(self, rule: PolicyRule, path: str) -> List[ValidationIssue]:
        """Validate a single policy rule."""
        issues = []
        
        # Validate rule name
        if not rule.name or len(rule.name.strip()) == 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="RULE_NAME_REQUIRED",
                message="Rule name is required",
                path=f"{path}.name",
                suggestion="Provide a descriptive name for the rule"
            ))
        
        # Validate roles
        for role in rule.roles:
            if not self.roles_api.is_valid_role(role):
                valid_roles = self.roles_api.get_role_names()
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_ROLE",
                    message=f"Unknown role: '{role}'",
                    path=f"{path}.roles",
                    suggestion=f"Valid roles are: {', '.join(valid_roles)}"
                ))
        
        # Validate resources
        for resource in rule.resources:
            if not self.resource_api.is_valid_resource(resource):
                valid_resources = self.resource_api.get_resource_names()
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_RESOURCE",
                    message=f"Unknown resource: '{resource}'",
                    path=f"{path}.resources",
                    suggestion=f"Valid resources are: {', '.join(valid_resources)}"
                ))
        
        # Validate permissions
        for permission in rule.permissions:
            if not self.roles_api.is_valid_permission(permission):
                valid_permissions = self.roles_api.get_permission_names()
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_PERMISSION",
                    message=f"Unknown permission: '{permission}'",
                    path=f"{path}.permissions",
                    suggestion=f"Valid permissions are: {', '.join(valid_permissions)}"
                ))
        
        # Validate permission-resource compatibility
        for resource in rule.resources:
            supported_actions = self.resource_api.get_supported_actions(resource)
            for permission in rule.permissions:
                if supported_actions and permission not in supported_actions:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="UNSUPPORTED_ACTION",
                        message=f"Action '{permission}' is not supported on resource '{resource}'",
                        path=f"{path}.permissions",
                        suggestion=f"Supported actions for {resource}: {', '.join(supported_actions)}"
                    ))
        
        # Validate conditions
        if rule.conditions:
            condition_issues = self._validate_condition_group(rule.conditions, f"{path}.conditions")
            issues.extend(condition_issues)
        
        # Check for overly broad rules
        if not rule.roles and not rule.resources and not rule.permissions:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="OVERLY_BROAD_RULE",
                message="Rule has no restrictions - it will match all requests",
                path=path,
                suggestion="Consider adding specific roles, resources, or permissions"
            ))
        
        return issues
    
    def _validate_condition_group(self, group: ConditionGroup, path: str) -> List[ValidationIssue]:
        """Validate a condition group and its nested conditions."""
        issues = []
        
        if not group.conditions:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="EMPTY_CONDITION_GROUP",
                message="Condition group has no conditions",
                path=path,
                suggestion="Add conditions or remove the empty group"
            ))
            return issues
        
        for i, condition in enumerate(group.conditions):
            if isinstance(condition, PolicyCondition):
                # Validate attribute exists
                if not self.context_api.is_valid_attribute(condition.attribute):
                    valid_attrs = self.context_api.get_attribute_names()
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_CONTEXT_ATTRIBUTE",
                        message=f"Unknown context attribute: '{condition.attribute}'",
                        path=f"{path}.conditions[{i}]",
                        suggestion=f"Valid attributes are: {', '.join(valid_attrs)}"
                    ))
                else:
                    # Validate attribute value
                    is_valid, error_msg = self.context_api.validate_attribute_value(
                        condition.attribute, condition.value
                    )
                    if not is_valid:
                        allowed = self.context_api.get_allowed_values(condition.attribute)
                        suggestion = f"Allowed values: {allowed}" if allowed else None
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            code="INVALID_ATTRIBUTE_VALUE",
                            message=error_msg,
                            path=f"{path}.conditions[{i}]",
                            suggestion=suggestion
                        ))
            
            elif isinstance(condition, ConditionGroup):
                # Recursively validate nested groups
                nested_issues = self._validate_condition_group(
                    condition, f"{path}.conditions[{i}]"
                )
                issues.extend(nested_issues)
        
        return issues
    
    def _validate_logical_consistency(self, policy: Policy) -> List[ValidationIssue]:
        """Check for logical consistency issues in the policy."""
        issues = []
        
        # Check for conflicting rules
        allow_rules = [r for r in policy.rules if r.effect.value == "ALLOW"]
        deny_rules = [r for r in policy.rules if r.effect.value == "DENY"]
        
        for allow_rule in allow_rules:
            for deny_rule in deny_rules:
                if self._rules_overlap(allow_rule, deny_rule):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="POTENTIALLY_CONFLICTING_RULES",
                        message=f"Rules '{allow_rule.name}' and '{deny_rule.name}' may conflict",
                        path=f"rules",
                        suggestion="Review rule priorities to ensure correct evaluation order"
                    ))
        
        return issues
    
    def _rules_overlap(self, rule1: PolicyRule, rule2: PolicyRule) -> bool:
        """Check if two rules might overlap."""
        # Check role overlap
        if rule1.roles and rule2.roles:
            if not set(rule1.roles) & set(rule2.roles):
                return False
        
        # Check resource overlap
        if rule1.resources and rule2.resources:
            if not set(rule1.resources) & set(rule2.resources):
                return False
        
        # Check permission overlap
        if rule1.permissions and rule2.permissions:
            if not set(rule1.permissions) & set(rule2.permissions):
                return False
        
        return True
    
    def _check_duplicate_rules(self, policy: Policy) -> List[ValidationIssue]:
        """Check for duplicate or redundant rules."""
        issues = []
        
        for i, rule1 in enumerate(policy.rules):
            for j, rule2 in enumerate(policy.rules[i + 1:], start=i + 1):
                if (set(rule1.roles) == set(rule2.roles) and
                    set(rule1.resources) == set(rule2.resources) and
                    set(rule1.permissions) == set(rule2.permissions) and
                    rule1.effect == rule2.effect):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="DUPLICATE_RULES",
                        message=f"Rules '{rule1.name}' and '{rule2.name}' appear to be duplicates",
                        path=f"rules[{i}], rules[{j}]",
                        suggestion="Remove or consolidate duplicate rules"
                    ))
        
        return issues
    
    def validate_rule(self, rule: PolicyRule) -> ValidationResult:
        """Validate a single rule (without full policy context)."""
        from datetime import datetime
        
        issues = self._validate_rule(rule, "rule")
        has_errors = any(issue.severity == ValidationSeverity.ERROR for issue in issues)
        
        return ValidationResult(
            is_valid=not has_errors,
            issues=issues,
            validated_at=datetime.utcnow().isoformat()
        )
