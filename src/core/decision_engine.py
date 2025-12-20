"""
Decision Engine - Evaluates access requests against policies.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import time

from src.models.policy import (
    Policy, PolicyRule, Decision,
    PolicyEvaluationRequest, PolicyEvaluationResult
)


class DecisionEngine:
    """
    Evaluates access requests against RBAC policies.
    Returns ALLOW or DENY decisions with explanations.
    """
    
    def __init__(self, policy: Optional[Policy] = None):
        self._policy = policy
    
    def set_policy(self, policy: Policy) -> None:
        """Set the policy to evaluate against."""
        self._policy = policy
    
    def get_policy(self) -> Optional[Policy]:
        """Get the current policy."""
        return self._policy
    
    def evaluate(
        self,
        role: str,
        resource: str,
        permission: str,
        context: Optional[Dict[str, Any]] = None
    ) -> PolicyEvaluationResult:
        """
        Evaluate an access request against the policy.
        
        Args:
            role: The role of the user making the request
            resource: The resource being accessed
            permission: The permission/action being requested
            context: Optional contextual attributes
        
        Returns:
            PolicyEvaluationResult with decision and explanation
        """
        start_time = time.time()
        context = context or {}
        
        if not self._policy:
            return PolicyEvaluationResult(
                decision=Decision.DENY,
                matched_rule=None,
                matched_rule_name=None,
                reason="No policy configured",
                evaluation_time_ms=(time.time() - start_time) * 1000
            )
        
        # Sort rules by priority (lower = higher priority)
        sorted_rules = sorted(self._policy.rules, key=lambda r: r.priority)
        
        # Find first matching rule
        for rule in sorted_rules:
            if rule.matches(role, resource, permission, context):
                return PolicyEvaluationResult(
                    decision=rule.effect,
                    matched_rule=rule.id,
                    matched_rule_name=rule.name,
                    reason=self._build_reason(rule, role, resource, permission, context),
                    evaluation_time_ms=(time.time() - start_time) * 1000
                )
        
        # No rule matched - use default decision
        return PolicyEvaluationResult(
            decision=self._policy.default_decision,
            matched_rule=None,
            matched_rule_name=None,
            reason=f"No matching rule found. Default decision: {self._policy.default_decision.value}",
            evaluation_time_ms=(time.time() - start_time) * 1000
        )
    
    def evaluate_request(self, request: PolicyEvaluationRequest) -> PolicyEvaluationResult:
        """Evaluate a PolicyEvaluationRequest object."""
        return self.evaluate(
            role=request.role,
            resource=request.resource,
            permission=request.permission,
            context=request.context
        )
    
    def evaluate_batch(
        self,
        requests: List[PolicyEvaluationRequest]
    ) -> List[PolicyEvaluationResult]:
        """Evaluate multiple requests in batch."""
        return [self.evaluate_request(req) for req in requests]
    
    def _build_reason(
        self,
        rule: PolicyRule,
        role: str,
        resource: str,
        permission: str,
        context: Dict[str, Any]
    ) -> str:
        """Build a human-readable explanation of the decision."""
        parts = [f"Rule '{rule.name}' matched:"]
        
        if rule.roles:
            parts.append(f"Role '{role}' is in allowed roles {rule.roles}")
        else:
            parts.append(f"Rule applies to all roles")
        
        if rule.resources:
            parts.append(f"Resource '{resource}' is in allowed resources {rule.resources}")
        else:
            parts.append(f"Rule applies to all resources")
        
        if rule.permissions:
            parts.append(f"Permission '{permission}' is in allowed permissions {rule.permissions}")
        else:
            parts.append(f"Rule applies to all permissions")
        
        if rule.conditions and context:
            parts.append(f"Context conditions were satisfied")
        
        parts.append(f"Decision: {rule.effect.value}")
        
        return " | ".join(parts)
    
    def get_effective_permissions(
        self,
        role: str,
        resource: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Decision]:
        """
        Get all effective permissions for a role on a resource.
        Returns a dict of permission -> decision.
        """
        context = context or {}
        permissions = ["read", "write", "delete", "create", "list", 
                       "export", "import", "approve", "reject", "execute", 
                       "configure", "audit"]
        
        results = {}
        for perm in permissions:
            result = self.evaluate(role, resource, perm, context)
            results[perm] = result.decision
        
        return results
    
    def explain_decision(
        self,
        role: str,
        resource: str,
        permission: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Provide a detailed explanation of a decision.
        Useful for debugging and auditing.
        """
        result = self.evaluate(role, resource, permission, context or {})
        
        explanation = {
            "request": {
                "role": role,
                "resource": resource,
                "permission": permission,
                "context": context or {}
            },
            "decision": result.decision.value,
            "matched_rule": result.matched_rule,
            "matched_rule_name": result.matched_rule_name,
            "reason": result.reason,
            "evaluation_time_ms": result.evaluation_time_ms,
            "policy_info": {
                "policy_name": self._policy.name if self._policy else None,
                "total_rules": len(self._policy.rules) if self._policy else 0,
                "default_decision": self._policy.default_decision.value if self._policy else None
            }
        }
        
        # Add rule details if a rule matched
        if result.matched_rule and self._policy:
            rule = self._policy.get_rule(result.matched_rule)
            if rule:
                explanation["matched_rule_details"] = {
                    "name": rule.name,
                    "description": rule.description,
                    "roles": rule.roles,
                    "resources": rule.resources,
                    "permissions": rule.permissions,
                    "effect": rule.effect.value,
                    "priority": rule.priority,
                    "has_conditions": rule.conditions is not None
                }
        
        return explanation
    
    def simulate_request(
        self,
        role: str,
        resource: str,
        permission: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Simulate a request and return detailed information.
        Useful for testing policies before deployment.
        """
        explanation = self.explain_decision(role, resource, permission, context)
        
        # Add simulation metadata
        explanation["simulation"] = {
            "timestamp": datetime.utcnow().isoformat(),
            "is_simulation": True,
            "warning": "This is a simulation. Actual behavior may vary in production."
        }
        
        return explanation
