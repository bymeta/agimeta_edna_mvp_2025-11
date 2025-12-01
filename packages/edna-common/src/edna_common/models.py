"""Pydantic models for Enterprise DNA"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class BusinessObject(BaseModel):
    """Represents a golden business object"""

    golden_id: str = Field(..., description="Deterministic hash of normalized keys")
    source_system: str = Field(..., description="Source system identifier")
    source_id: str = Field(..., description="Source system's ID for this object")
    object_type: str = Field(..., description="Type of business object")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Object attributes")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "golden_id": "a1b2c3d4e5f6",
                "source_system": "crm",
                "source_id": "12345",
                "object_type": "customer",
                "attributes": {"name": "Acme Corp", "email": "contact@acme.com"},
            }
        }


class Event(BaseModel):
    """Represents an event in the system"""

    event_id: Optional[str] = Field(None, description="Unique event identifier")
    event_type: str = Field(..., description="Type of event")
    golden_id: Optional[str] = Field(None, description="Associated golden object ID")
    source_system: str = Field(..., description="Source system identifier")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event payload")
    occurred_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "object.created",
                "golden_id": "a1b2c3d4e5f6",
                "source_system": "crm",
                "payload": {"action": "create", "object_id": "12345"},
            }
        }


class MatchRule(BaseModel):
    """Rule for deterministic matching"""

    rule_id: str = Field(..., description="Unique rule identifier")
    rule_name: str = Field(..., description="Human-readable rule name")
    object_type: str = Field(..., description="Object type this rule applies to")
    source_system: str = Field(..., description="Source system this rule applies to")
    key_fields: list[str] = Field(..., description="List of fields to use for matching")
    normalization_rules: Dict[str, str] = Field(
        default_factory=dict, description="Field normalization rules"
    )
    active: bool = Field(default=True, description="Whether rule is active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "rule_id": "rule-001",
                "rule_name": "Customer Email Match",
                "object_type": "customer",
                "source_system": "crm",
                "key_fields": ["email", "phone"],
                "normalization_rules": {"email": "lowercase", "phone": "digits_only"},
            }
        }

