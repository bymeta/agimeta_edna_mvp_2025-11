"""Tests for Pydantic models"""

import pytest
from datetime import datetime
from edna_common.models import BusinessObject, Event, MatchRule


def test_business_object():
    """Test BusinessObject model"""
    obj = BusinessObject(
        golden_id="test-123",
        source_system="crm",
        source_id="456",
        object_type="customer",
        attributes={"name": "Test Corp"}
    )
    assert obj.golden_id == "test-123"
    assert obj.source_system == "crm"
    assert obj.attributes == {"name": "Test Corp"}


def test_event():
    """Test Event model"""
    event = Event(
        event_type="object.created",
        source_system="crm",
        payload={"action": "create"}
    )
    assert event.event_type == "object.created"
    assert event.source_system == "crm"
    assert isinstance(event.occurred_at, datetime)


def test_match_rule():
    """Test MatchRule model"""
    rule = MatchRule(
        rule_id="rule-001",
        rule_name="Test Rule",
        object_type="customer",
        source_system="crm",
        key_fields=["email", "phone"]
    )
    assert rule.rule_id == "rule-001"
    assert rule.active is True
    assert "email" in rule.key_fields

