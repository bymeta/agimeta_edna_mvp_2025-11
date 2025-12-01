"""Tests for identity matching"""

import pytest
from identity.matcher import IdentityMatcher


def test_normalize_value():
    """Test value normalization"""
    matcher = IdentityMatcher("postgresql://test:test@localhost/test")
    
    assert matcher.normalize_value("  TEST  ", "trim") == "TEST"
    assert matcher.normalize_value("Test@Example.COM", "lowercase") == "test@example.com"
    assert matcher.normalize_value("(555) 123-4567", "digits_only") == "5551234567"
    assert matcher.normalize_value("Test123!", "alphanumeric_only") == "Test123"


def test_compute_golden_id():
    """Test golden ID computation"""
    matcher = IdentityMatcher("postgresql://test:test@localhost/test")
    
    source_data = {
        "email": "test@example.com",
        "phone": "555-1234"
    }
    key_fields = ["email", "phone"]
    normalization_rules = {"email": "lowercase", "phone": "digits_only"}
    
    golden_id = matcher.compute_golden_id(source_data, key_fields, normalization_rules)
    
    # Should be deterministic
    golden_id2 = matcher.compute_golden_id(source_data, key_fields, normalization_rules)
    assert golden_id == golden_id2
    
    # Should be different with different data
    source_data2 = {"email": "other@example.com", "phone": "555-1234"}
    golden_id3 = matcher.compute_golden_id(source_data2, key_fields, normalization_rules)
    assert golden_id != golden_id3

