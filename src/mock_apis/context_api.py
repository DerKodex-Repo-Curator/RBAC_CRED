"""
Mock Context Schema API.
Provides available contextual attributes and their data types.
"""

from typing import List, Dict, Optional, Any
from src.models.context import ContextAttribute, ContextSchema, AttributeType


class ContextSchemaAPI:
    """
    Mock API for discovering available context attributes.
    In a real system, this would connect to a context provider.
    """
    
    def __init__(self):
        # Simulated database of context attributes
        self._attributes: Dict[str, ContextAttribute] = {
            "environment": ContextAttribute(
                name="environment",
                type=AttributeType.ENUM,
                description="Deployment environment",
                allowed_values=["production", "staging", "development", "testing"],
                default_value="production"
            ),
            "time_of_day": ContextAttribute(
                name="time_of_day",
                type=AttributeType.ENUM,
                description="Time period of the day",
                allowed_values=["morning", "afternoon", "evening", "night", "business_hours", "off_hours"],
                default_value="business_hours"
            ),
            "day_of_week": ContextAttribute(
                name="day_of_week",
                type=AttributeType.ENUM,
                description="Day of the week",
                allowed_values=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "weekday", "weekend"],
                default_value="weekday"
            ),
            "ip_range": ContextAttribute(
                name="ip_range",
                type=AttributeType.STRING,
                description="IP address range (CIDR notation)",
                allowed_values=None,
                default_value=None
            ),
            "country": ContextAttribute(
                name="country",
                type=AttributeType.STRING,
                description="Country code (ISO 3166-1 alpha-2)",
                allowed_values=None,
                default_value=None
            ),
            "region": ContextAttribute(
                name="region",
                type=AttributeType.ENUM,
                description="Geographic region",
                allowed_values=["us-east", "us-west", "eu-west", "eu-central", "asia-pacific", "global"],
                default_value="global"
            ),
            "device_type": ContextAttribute(
                name="device_type",
                type=AttributeType.ENUM,
                description="Type of device making the request",
                allowed_values=["desktop", "mobile", "tablet", "api", "service"],
                default_value="desktop"
            ),
            "authentication_method": ContextAttribute(
                name="authentication_method",
                type=AttributeType.ENUM,
                description="How the user authenticated",
                allowed_values=["password", "sso", "mfa", "api_key", "oauth", "certificate"],
                default_value="password"
            ),
            "mfa_verified": ContextAttribute(
                name="mfa_verified",
                type=AttributeType.BOOLEAN,
                description="Whether MFA was verified",
                allowed_values=None,
                default_value=False
            ),
            "session_age_minutes": ContextAttribute(
                name="session_age_minutes",
                type=AttributeType.INTEGER,
                description="Age of the current session in minutes",
                allowed_values=None,
                default_value=0
            ),
            "request_rate": ContextAttribute(
                name="request_rate",
                type=AttributeType.INTEGER,
                description="Number of requests in the last minute",
                allowed_values=None,
                default_value=0
            ),
            "risk_score": ContextAttribute(
                name="risk_score",
                type=AttributeType.FLOAT,
                description="Calculated risk score (0.0 - 1.0)",
                allowed_values=None,
                default_value=0.0
            ),
            "department": ContextAttribute(
                name="department",
                type=AttributeType.STRING,
                description="User's department",
                allowed_values=None,
                default_value=None
            ),
            "team": ContextAttribute(
                name="team",
                type=AttributeType.STRING,
                description="User's team",
                allowed_values=None,
                default_value=None
            ),
            "resource_owner": ContextAttribute(
                name="resource_owner",
                type=AttributeType.BOOLEAN,
                description="Whether the user owns the resource",
                allowed_values=None,
                default_value=False
            ),
            "is_sensitive": ContextAttribute(
                name="is_sensitive",
                type=AttributeType.BOOLEAN,
                description="Whether the resource is marked as sensitive",
                allowed_values=None,
                default_value=False
            ),
            "data_classification": ContextAttribute(
                name="data_classification",
                type=AttributeType.ENUM,
                description="Data classification level",
                allowed_values=["public", "internal", "confidential", "restricted"],
                default_value="internal"
            ),
        }
    
    def get_all_attributes(self) -> List[ContextAttribute]:
        """Get all available context attributes."""
        return list(self._attributes.values())
    
    def get_attribute(self, name: str) -> Optional[ContextAttribute]:
        """Get a specific attribute by name."""
        return self._attributes.get(name.lower())
    
    def get_attribute_names(self) -> List[str]:
        """Get all attribute names."""
        return list(self._attributes.keys())
    
    def is_valid_attribute(self, name: str) -> bool:
        """Check if an attribute name is valid."""
        return name.lower() in self._attributes
    
    def get_attribute_type(self, name: str) -> Optional[AttributeType]:
        """Get the type of an attribute."""
        attr = self.get_attribute(name)
        if attr:
            return attr.type
        return None
    
    def get_allowed_values(self, name: str) -> Optional[List[Any]]:
        """Get allowed values for an enum attribute."""
        attr = self.get_attribute(name)
        if attr and attr.allowed_values:
            return attr.allowed_values
        return None
    
    def validate_attribute_value(self, name: str, value: Any) -> tuple[bool, str]:
        """
        Validate an attribute value.
        Returns (is_valid, error_message).
        """
        attr = self.get_attribute(name)
        if not attr:
            return False, f"Unknown attribute: {name}"
        
        # Type validation
        if attr.type == AttributeType.STRING:
            if not isinstance(value, str):
                return False, f"Attribute {name} must be a string"
        
        elif attr.type == AttributeType.INTEGER:
            if not isinstance(value, int):
                return False, f"Attribute {name} must be an integer"
        
        elif attr.type == AttributeType.FLOAT:
            if not isinstance(value, (int, float)):
                return False, f"Attribute {name} must be a number"
        
        elif attr.type == AttributeType.BOOLEAN:
            if not isinstance(value, bool):
                return False, f"Attribute {name} must be a boolean"
        
        elif attr.type == AttributeType.ENUM:
            if attr.allowed_values and value not in attr.allowed_values:
                return False, f"Attribute {name} must be one of: {attr.allowed_values}"
        
        return True, ""
    
    def get_schema(self) -> ContextSchema:
        """Get the complete context schema."""
        return ContextSchema(attributes=self.get_all_attributes())
    
    def discover(self) -> Dict:
        """
        Discovery endpoint - returns all context attributes.
        This is the main API endpoint that would be called for discovery.
        """
        return {
            "attributes": [attr.model_dump() for attr in self.get_all_attributes()],
        }
