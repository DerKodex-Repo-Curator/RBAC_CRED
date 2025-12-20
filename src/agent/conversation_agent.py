"""
Conversation Agent - Interprets natural language policy instructions using Claude.
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

import anthropic
from dotenv import load_dotenv

from src.models.policy import (
    Policy, PolicyRule, PolicyCondition, ConditionGroup,
    Decision, LogicalOperator, ComparisonOperator
)
from src.core.policy_builder import PolicyBuilder
from src.core.schema_cache import SchemaCache
from src.mock_apis import RolesPermissionsAPI, ResourceSchemaAPI, ContextSchemaAPI

load_dotenv()


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ConversationState:
    """Tracks the state of the conversation."""
    messages: List[Message] = field(default_factory=list)
    pending_clarifications: List[str] = field(default_factory=list)
    last_intent: Optional[str] = None
    current_rule_draft: Optional[Dict] = None
    
    def add_message(self, role: MessageRole, content: str) -> Message:
        msg = Message(role=role, content=content)
        self.messages.append(msg)
        return msg
    
    def get_conversation_history(self) -> List[Dict]:
        """Get history in Claude-compatible format."""
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in self.messages
            if msg.role != MessageRole.SYSTEM
        ]


class ConversationAgent:
    """
    AI-powered agent for interpreting natural language policy instructions.
    Uses Claude to understand user intent and ask clarifying questions.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        policy_builder: Optional[PolicyBuilder] = None,
        schema_cache: Optional[SchemaCache] = None
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        
        # Initialize components
        self.roles_api = RolesPermissionsAPI()
        self.resource_api = ResourceSchemaAPI()
        self.context_api = ContextSchemaAPI()
        
        self.schema_cache = schema_cache or SchemaCache()
        self.policy_builder = policy_builder or PolicyBuilder(
            self.roles_api, self.resource_api, self.context_api
        )
        
        # Conversation state
        self.state = ConversationState()
        
        # Cache schemas on init
        self._cached_schemas = self.schema_cache.discover_and_cache_schemas(
            self.roles_api, self.resource_api, self.context_api
        )
    
    def _get_system_prompt(self) -> str:
        """Generate the system prompt with schema information."""
        roles = self._cached_schemas["roles"]["roles"]
        resources = self._cached_schemas["resources"]["resources"]
        context_attrs = self._cached_schemas["context"]["attributes"]
        permissions = self._cached_schemas["roles"]["permissions"]
        
        role_names = [r["name"] for r in roles]
        resource_names = [r["name"] for r in resources]
        permission_names = [p["name"] for p in permissions]
        context_names = [a["name"] for a in context_attrs]
        
        # Build resource-action mapping
        resource_actions = {}
        for r in resources:
            resource_actions[r["name"]] = r["supported_actions"]
        
        # Build context attribute details
        context_details = []
        for attr in context_attrs:
            detail = f"- {attr['name']} ({attr['type']})"
            if attr.get('allowed_values'):
                detail += f": {attr['allowed_values']}"
            context_details.append(detail)
        
        return f"""You are an RBAC (Role-Based Access Control) policy assistant. Your job is to help users create access control policies through natural language conversation.

## Available Schema

### Roles
{json.dumps(role_names, indent=2)}

### Permissions/Actions
{json.dumps(permission_names, indent=2)}

### Resources
{json.dumps(resource_names, indent=2)}

### Resource-Action Compatibility
{json.dumps(resource_actions, indent=2)}

### Context Attributes (for conditions)
{chr(10).join(context_details)}

## Your Responsibilities

1. **Interpret user intent**: Understand what policy rule the user wants to create
2. **Ask clarifying questions**: If the user's request is ambiguous, ask specific questions
3. **Validate against schema**: Reject unknown roles, resources, or permissions with helpful feedback
4. **Suggest corrections**: If user mentions something close to a valid value, suggest the correct one

## Response Format

Always respond with a JSON object in this exact format:

```json
{{
  "type": "clarification" | "rule_created" | "error" | "info" | "validation",
  "message": "Human-readable message to show the user",
  "clarification_questions": ["Question 1?", "Question 2?"],  // Only for type=clarification
  "rule": {{  // Only for type=rule_created
    "name": "rule name",
    "roles": ["role1"],
    "resources": ["resource1"],
    "permissions": ["read", "write"],
    "effect": "ALLOW" | "DENY",
    "conditions": null | {{
      "operator": "AND" | "OR",
      "conditions": [
        {{"attribute": "environment", "operator": "equals", "value": "production"}}
      ]
    }},
    "description": "What this rule does"
  }},
  "suggestions": ["suggestion1", "suggestion2"],  // Helpful suggestions
  "needs_more_info": true | false
}}
```

## Clarification Examples

- If user says "Operators can edit" → Ask: "Which resource should operators be able to edit? (e.g., invoice, report, user_profile)"
- If user says "Allow access in production" → Ask: "Who should have access? What resource? What actions?"
- If user says "Admin can do everything" → Create rule with all permissions on all resources

## Validation Rules

1. Only accept roles from the available list
2. Only accept resources from the available list  
3. Only accept permissions that are supported by the specified resource
4. Context attribute values must match allowed values for enum types
5. Logical operators: AND, OR, NOT

## Important Guidelines

- Be helpful and guide users through policy creation
- Always validate before confirming rule creation
- Explain WHY something is invalid
- Suggest the closest valid alternative when rejecting input
- Keep responses concise but informative"""
    
    def process_message(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user message and return a response.
        
        Returns a dict with:
        - type: clarification, rule_created, error, info, validation
        - message: Human-readable response
        - rule: Created rule (if applicable)
        - needs_more_info: Whether more info is needed
        """
        # Add user message to history
        self.state.add_message(MessageRole.USER, user_message)
        
        # Check for special commands
        special_response = self._handle_special_commands(user_message)
        if special_response:
            return special_response
        
        # Call Claude to interpret the message
        try:
            response = self._call_claude(user_message)
            parsed = self._parse_response(response)
            
            # If a rule was created, add it to the policy
            if parsed.get("type") == "rule_created" and parsed.get("rule"):
                result = self._add_rule_from_response(parsed["rule"])
                if not result["success"]:
                    parsed["type"] = "error"
                    parsed["message"] = result["message"]
                else:
                    parsed["message"] = f"✅ {result['message']}\n\n{parsed['message']}"
            
            # Add assistant response to history
            self.state.add_message(MessageRole.ASSISTANT, parsed["message"])
            
            return parsed
            
        except Exception as e:
            error_response = {
                "type": "error",
                "message": f"Error processing request: {str(e)}",
                "needs_more_info": False
            }
            self.state.add_message(MessageRole.ASSISTANT, error_response["message"])
            return error_response
    
    def _call_claude(self, user_message: str) -> str:
        """Call Claude API with the conversation history."""
        messages = self.state.get_conversation_history()
        
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=self._get_system_prompt(),
            messages=messages
        )
        
        return response.content[0].text
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse Claude's response into a structured format."""
        # Try to extract JSON from the response
        try:
            # Look for JSON in code blocks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "{" in response:
                # Try to find JSON object
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]
            else:
                # No JSON found, return as info message
                return {
                    "type": "info",
                    "message": response,
                    "needs_more_info": False
                }
            
            parsed = json.loads(json_str)
            
            # Ensure required fields
            if "type" not in parsed:
                parsed["type"] = "info"
            if "message" not in parsed:
                parsed["message"] = response
            if "needs_more_info" not in parsed:
                parsed["needs_more_info"] = parsed["type"] == "clarification"
            
            return parsed
            
        except json.JSONDecodeError:
            # If JSON parsing fails, return as info message
            return {
                "type": "info",
                "message": response,
                "needs_more_info": False
            }
    
    def _add_rule_from_response(self, rule_data: Dict) -> Dict[str, Any]:
        """Add a rule to the policy from Claude's response."""
        # Ensure policy exists
        if not self.policy_builder.get_policy():
            self.policy_builder.create_policy()
        
        # Build conditions if present
        conditions = None
        if rule_data.get("conditions"):
            cond_data = rule_data["conditions"]
            conditions = self._build_conditions(cond_data)
        
        # Parse effect
        effect = Decision.ALLOW
        if rule_data.get("effect", "").upper() == "DENY":
            effect = Decision.DENY
        
        # Add the rule
        success, message, rule = self.policy_builder.add_rule(
            name=rule_data.get("name", "Unnamed Rule"),
            roles=rule_data.get("roles", []),
            resources=rule_data.get("resources", []),
            permissions=rule_data.get("permissions", []),
            effect=effect,
            conditions=conditions,
            description=rule_data.get("description")
        )
        
        return {"success": success, "message": message, "rule": rule}
    
    def _build_conditions(self, cond_data: Dict) -> Optional[ConditionGroup]:
        """Build a ConditionGroup from parsed condition data."""
        if not cond_data:
            return None
        
        operator = LogicalOperator(cond_data.get("operator", "AND"))
        conditions = []
        
        for cond in cond_data.get("conditions", []):
            if "conditions" in cond:
                # Nested condition group
                nested = self._build_conditions(cond)
                if nested:
                    conditions.append(nested)
            else:
                # Simple condition
                try:
                    comp_op = ComparisonOperator(cond.get("operator", "equals"))
                    conditions.append(PolicyCondition(
                        attribute=cond["attribute"],
                        operator=comp_op,
                        value=cond["value"]
                    ))
                except (KeyError, ValueError):
                    continue
        
        if conditions:
            return ConditionGroup(operator=operator, conditions=conditions)
        return None
    
    def _handle_special_commands(self, message: str) -> Optional[Dict]:
        """Handle special commands like 'show policy', 'validate', etc."""
        message_lower = message.lower().strip()
        
        if message_lower in ["show policy", "view policy", "display policy"]:
            policy = self.policy_builder.get_policy()
            if policy:
                return {
                    "type": "info",
                    "message": f"Current policy has {len(policy.rules)} rules.",
                    "policy": policy.to_json(),
                    "needs_more_info": False
                }
            return {
                "type": "info",
                "message": "No policy created yet. Start by describing a rule.",
                "needs_more_info": False
            }
        
        if message_lower in ["validate", "check policy", "validate policy"]:
            is_valid, report = self.policy_builder.validate_policy()
            return {
                "type": "validation",
                "message": "✅ Policy is valid!" if is_valid else "❌ Policy has issues.",
                "validation_report": report,
                "needs_more_info": False
            }
        
        if message_lower in ["help", "commands", "?"]:
            return {
                "type": "info",
                "message": self._get_help_message(),
                "needs_more_info": False
            }
        
        if message_lower in ["clear", "reset", "start over"]:
            self.policy_builder.create_policy()
            self.state = ConversationState()
            return {
                "type": "info",
                "message": "Policy cleared. Starting fresh!",
                "needs_more_info": False
            }
        
        if message_lower.startswith("list "):
            return self._handle_list_command(message_lower[5:])
        
        return None
    
    def _handle_list_command(self, what: str) -> Dict:
        """Handle 'list roles/resources/permissions' commands."""
        what = what.strip()
        
        if what == "roles":
            roles = self.policy_builder.get_available_roles()
            return {
                "type": "info",
                "message": f"**Available Roles:**\n" + "\n".join(f"- {r}" for r in roles),
                "needs_more_info": False
            }
        
        if what in ["resources", "resource"]:
            resources = self.policy_builder.get_available_resources()
            return {
                "type": "info",
                "message": f"**Available Resources:**\n" + "\n".join(f"- {r}" for r in resources),
                "needs_more_info": False
            }
        
        if what in ["permissions", "actions"]:
            perms = self.policy_builder.get_available_permissions()
            return {
                "type": "info",
                "message": f"**Available Permissions:**\n" + "\n".join(f"- {p}" for p in perms),
                "needs_more_info": False
            }
        
        if what in ["context", "attributes", "context attributes"]:
            attrs = self.policy_builder.get_available_context_attributes()
            return {
                "type": "info",
                "message": f"**Available Context Attributes:**\n" + "\n".join(f"- {a}" for a in attrs),
                "needs_more_info": False
            }
        
        return {
            "type": "info",
            "message": "Unknown list command. Try: list roles, list resources, list permissions, list context",
            "needs_more_info": False
        }
    
    def _get_help_message(self) -> str:
        """Return help message."""
        return """# RBAC Policy Engine Help

## Natural Language Examples
- "Admins can do everything"
- "Viewers can only read invoices"
- "Operators can edit orders in production"
- "Deny delete access to guests"
- "Allow analysts to export reports during business hours"

## Commands
- `list roles` - Show available roles
- `list resources` - Show available resources
- `list permissions` - Show available permissions
- `list context` - Show context attributes
- `show policy` - View current policy
- `validate` - Validate the policy
- `clear` - Start over with a new policy
- `help` - Show this message

## Tips
- Be specific about roles, resources, and permissions
- Use context attributes for conditional access
- I'll ask clarifying questions if anything is unclear
"""
    
    def get_current_policy(self) -> Optional[Policy]:
        """Get the current policy being built."""
        return self.policy_builder.get_policy()
    
    def get_policy_json(self) -> Optional[str]:
        """Get the current policy as JSON."""
        return self.policy_builder.export_policy_json()
    
    def validate_current_policy(self) -> Tuple[bool, Dict]:
        """Validate the current policy."""
        return self.policy_builder.validate_policy()
    
    def get_conversation_history(self) -> List[Dict]:
        """Get the conversation history."""
        return [msg.to_dict() for msg in self.state.messages]
    
    def clear_conversation(self) -> None:
        """Clear conversation history but keep the policy."""
        self.state = ConversationState()
