"""
Policy Builder - Constructs RBAC policies from user instructions.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json

from src.models.policy import (
    Policy, PolicyRule, PolicyCondition, ConditionGroup,
    Decision, LogicalOperator, ComparisonOperator
)
from src.mock_apis import RolesPermissionsAPI, ResourceSchemaAPI, ContextSchemaAPI, PolicyValidatorAPI


class PolicyBuilder:
    """
    Builds RBAC policies from structured inputs.
    Validates all inputs against discovered schemas.
    """
    
    def __init__(
        self,
        roles_api: Optional[RolesPermissionsAPI] = None,
        resource_api: Optional[ResourceSchemaAPI] = None,
        context_api: Optional[ContextSchemaAPI] = None,
        validator_api: Optional[PolicyValidatorAPI] = None
    ):
        self.roles_api = roles_api or RolesPermissionsAPI()
        self.resource_api = resource_api or ResourceSchemaAPI()
        self.context_api = context_api or ContextSchemaAPI()
        self.validator_api = validator_api or PolicyValidatorAPI(
            self.roles_api, self.resource_api, self.context_api
        )
        
        # Current policy being built
        self._policy: Optional[Policy] = None
    
    def create_policy(
        self,
        name: str = "RBAC Policy",
        description: Optional[str] = None,
        default_decision: Decision = Decision.DENY
    ) -> Policy:
        """Create a new empty policy."""
        self._policy = Policy(
            name=name,
            description=description,
            default_decision=default_decision,
            rules=[]
        )
        return self._policy
    
    def get_policy(self) -> Optional[Policy]:
        """Get the current policy being built."""
        return self._policy
    
    def set_policy(self, policy: Policy) -> None:
        """Set an existing policy to continue building."""
        self._policy = policy
    
    def add_rule(
        self,
        name: str,
        roles: List[str],
        resources: List[str],
        permissions: List[str],
        effect: Decision = Decision.ALLOW,
        conditions: Optional[ConditionGroup] = None,
        description: Optional[str] = None,
        priority: int = 100
    ) -> Tuple[bool, str, Optional[PolicyRule]]:
        """
        Add a new rule to the policy.
        Returns (success, message, rule).
        """
        if not self._policy:
            return False, "No policy initialized. Call create_policy() first.", None
        
        # Validate inputs before creating rule
        errors = []
        
        # Validate roles
        for role in roles:
            if not self.roles_api.is_valid_role(role):
                valid = self.roles_api.get_role_names()
                errors.append(f"Unknown role '{role}'. Valid roles: {', '.join(valid)}")
        
        # Validate resources
        for resource in resources:
            if not self.resource_api.is_valid_resource(resource):
                valid = self.resource_api.get_resource_names()
                errors.append(f"Unknown resource '{resource}'. Valid resources: {', '.join(valid)}")
        
        # Validate permissions
        for permission in permissions:
            if not self.roles_api.is_valid_permission(permission):
                valid = self.roles_api.get_permission_names()
                errors.append(f"Unknown permission '{permission}'. Valid permissions: {', '.join(valid)}")
        
        # Validate resource-permission compatibility
        for resource in resources:
            supported = self.resource_api.get_supported_actions(resource)
            for permission in permissions:
                if supported and permission not in supported:
                    errors.append(
                        f"Action '{permission}' not supported on '{resource}'. "
                        f"Supported: {', '.join(supported)}"
                    )
        
        if errors:
            return False, " | ".join(errors), None
        
        # Create the rule
        rule = PolicyRule(
            name=name,
            description=description,
            roles=roles,
            resources=resources,
            permissions=permissions,
            conditions=conditions,
            effect=effect,
            priority=priority
        )
        
        self._policy.add_rule(rule)
        return True, f"Rule '{name}' added successfully.", rule
    
    def create_condition(
        self,
        attribute: str,
        operator: str,
        value: Any
    ) -> Tuple[bool, str, Optional[PolicyCondition]]:
        """
        Create a policy condition.
        Returns (success, message, condition).
        """
        # Validate attribute
        if not self.context_api.is_valid_attribute(attribute):
            valid = self.context_api.get_attribute_names()
            return False, f"Unknown attribute '{attribute}'. Valid: {', '.join(valid)}", None
        
        # Validate value
        is_valid, error_msg = self.context_api.validate_attribute_value(attribute, value)
        if not is_valid:
            allowed = self.context_api.get_allowed_values(attribute)
            hint = f" Allowed: {allowed}" if allowed else ""
            return False, f"{error_msg}.{hint}", None
        
        # Parse operator
        try:
            op = ComparisonOperator(operator.lower())
        except ValueError:
            valid_ops = [o.value for o in ComparisonOperator]
            return False, f"Unknown operator '{operator}'. Valid: {', '.join(valid_ops)}", None
        
        condition = PolicyCondition(attribute=attribute, operator=op, value=value)
        return True, "Condition created.", condition
    
    def create_condition_group(
        self,
        conditions: List[PolicyCondition],
        operator: LogicalOperator = LogicalOperator.AND
    ) -> ConditionGroup:
        """Create a condition group from multiple conditions."""
        return ConditionGroup(operator=operator, conditions=conditions)
    
    def remove_rule(self, rule_id: str) -> Tuple[bool, str]:
        """Remove a rule from the policy."""
        if not self._policy:
            return False, "No policy initialized."
        
        if self._policy.remove_rule(rule_id):
            return True, f"Rule '{rule_id}' removed."
        return False, f"Rule '{rule_id}' not found."
    
    def update_rule(
        self,
        rule_id: str,
        **updates
    ) -> Tuple[bool, str]:
        """Update an existing rule."""
        if not self._policy:
            return False, "No policy initialized."
        
        rule = self._policy.get_rule(rule_id)
        if not rule:
            return False, f"Rule '{rule_id}' not found."
        
        # Get index and remove old rule
        for i, r in enumerate(self._policy.rules):
            if r.id == rule_id:
                # Create updated rule
                rule_dict = rule.model_dump()
                rule_dict.update(updates)
                
                # Validate updates
                if 'roles' in updates:
                    for role in updates['roles']:
                        if not self.roles_api.is_valid_role(role):
                            return False, f"Unknown role '{role}'"
                
                if 'resources' in updates:
                    for resource in updates['resources']:
                        if not self.resource_api.is_valid_resource(resource):
                            return False, f"Unknown resource '{resource}'"
                
                if 'permissions' in updates:
                    for perm in updates['permissions']:
                        if not self.roles_api.is_valid_permission(perm):
                            return False, f"Unknown permission '{perm}'"
                
                # Apply update
                try:
                    new_rule = PolicyRule(**rule_dict)
                    self._policy.rules[i] = new_rule
                    self._policy.updated_at = datetime.utcnow()
                    return True, f"Rule '{rule_id}' updated."
                except Exception as e:
                    return False, f"Update failed: {str(e)}"
        
        return False, f"Rule '{rule_id}' not found."
    
    def validate_policy(self) -> Tuple[bool, Dict]:
        """Validate the current policy."""
        if not self._policy:
            return False, {"error": "No policy initialized."}
        
        result = self.validator_api.validate(self._policy)
        return result.is_valid, result.to_dict()
    
    def get_available_roles(self) -> List[str]:
        """Get all available role names."""
        return self.roles_api.get_role_names()
    
    def get_available_resources(self) -> List[str]:
        """Get all available resource names."""
        return self.resource_api.get_resource_names()
    
    def get_available_permissions(self) -> List[str]:
        """Get all available permission names."""
        return self.roles_api.get_permission_names()
    
    def get_available_context_attributes(self) -> List[str]:
        """Get all available context attribute names."""
        return self.context_api.get_attribute_names()
    
    def get_resource_actions(self, resource: str) -> List[str]:
        """Get supported actions for a specific resource."""
        return self.resource_api.get_supported_actions(resource)
    
    def get_attribute_info(self, attribute: str) -> Optional[Dict]:
        """Get info about a context attribute."""
        attr = self.context_api.get_attribute(attribute)
        if attr:
            return attr.model_dump()
        return None
    
    def export_policy(self) -> Optional[Dict]:
        """Export the policy as a JSON-serializable dict."""
        if not self._policy:
            return None
        return self._policy.to_json()
    
    def export_policy_json(self) -> Optional[str]:
        """Export the policy as a JSON string."""
        policy_dict = self.export_policy()
        if policy_dict:
            return json.dumps(policy_dict, indent=2, default=str)
        return None
    
    def import_policy(self, policy_dict: Dict) -> Tuple[bool, str]:
        """Import a policy from a dictionary."""
        try:
            self._policy = Policy(**policy_dict)
            return True, "Policy imported successfully."
        except Exception as e:
            return False, f"Import failed: {str(e)}"
