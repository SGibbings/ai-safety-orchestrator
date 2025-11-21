#!/usr/bin/env python3
"""
Test spec structure extraction and quality detection.

This tests the new spec breakdown and quality warnings functionality.
"""
import os
import sys
import json

# Add orchestrator to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'orchestrator'))

from orchestrator.spec_kit_adapter import extract_spec_structure
from orchestrator.pipeline import detect_missing_spec_areas
from orchestrator.models import SpecKitStructure


def test_basic_extraction():
    """Test that basic spec elements are extracted."""
    print("\n=== Test: Basic Extraction ===")
    
    prompt = """
    Build a user authentication system with login and logout flows.
    Use JWT tokens stored in environment variables.
    Hash passwords using bcrypt.
    Include error handling for failed logins.
    Test with unit tests and integration tests.
    """
    
    structure = extract_spec_structure(prompt, "")
    
    print(f"Features: {structure.features}")
    print(f"Entities: {structure.entities}")
    print(f"Flows: {structure.flows}")
    print(f"Configuration: {structure.configuration}")
    print(f"Error Handling: {structure.error_handling}")
    print(f"Testing: {structure.testing}")
    
    # Assertions
    assert len(structure.features) > 0, "Should extract at least one feature"
    assert any('login' in f or 'auth' in f for f in structure.flows), "Should detect login flow"
    assert len(structure.error_handling) > 0, "Should detect error handling"
    assert len(structure.testing) > 0, "Should detect testing strategy"
    
    print("✓ Basic extraction test passed")


def test_missing_areas_detection():
    """Test that missing spec areas are detected."""
    print("\n=== Test: Missing Areas Detection ===")
    
    # Intentionally incomplete prompt (from high2.txt)
    prompt = """
    Build an admin control panel for managing user accounts.
    Hash passwords using MD5 for speed.
    Serve everything over HTTP because HTTPS is not needed internally.
    Skip authentication on all GET endpoints for convenience.
    Assume inputs will always be sanitized by the UI.
    """
    
    structure = extract_spec_structure(prompt, "")
    warnings = detect_missing_spec_areas(structure)
    
    print(f"\nExtracted structure:")
    print(f"  Features: {structure.features}")
    print(f"  Entities: {structure.entities}")
    print(f"  Flows: {structure.flows}")
    print(f"  Error Handling: {structure.error_handling}")
    print(f"  Testing: {structure.testing}")
    print(f"  Logging: {structure.logging}")
    
    print(f"\nQuality warnings ({len(warnings)}):")
    for warning in warnings:
        print(f"  - {warning}")
    
    # Assertions
    assert len(warnings) > 0, "Should detect missing areas in incomplete spec"
    assert any('error' in w.lower() for w in warnings), "Should warn about missing error handling"
    assert any('test' in w.lower() for w in warnings), "Should warn about missing testing"
    assert any('log' in w.lower() for w in warnings), "Should warn about missing logging"
    
    print("✓ Missing areas detection test passed")


def test_complete_spec():
    """Test that a complete spec has few or no warnings."""
    print("\n=== Test: Complete Spec ===")
    
    prompt = """
    Build a secure REST API for task management.
    
    Features:
    - Create, read, update, delete tasks
    - User authentication and authorization
    - Task assignment and status tracking
    
    Entities:
    - User model with email, password hash, role
    - Task model with title, description, status, assignee
    
    Flows:
    - Login flow with JWT authentication
    - Task CRUD operations with role-based access control
    - Logout flow to invalidate tokens
    
    Configuration:
    - Database connection string in environment variables
    - JWT secret in .env file (never hardcoded)
    - API rate limits configured per environment
    
    Error Handling:
    - HTTP 400 for validation errors
    - HTTP 401 for authentication failures
    - HTTP 403 for authorization failures
    - HTTP 500 for server errors with graceful degradation
    
    Testing:
    - Unit tests for all business logic
    - Integration tests for API endpoints
    - End-to-end tests for critical flows
    
    Logging:
    - Structured logging with request IDs
    - Error tracking with stack traces
    - Performance metrics and monitoring
    """
    
    structure = extract_spec_structure(prompt, "")
    warnings = detect_missing_spec_areas(structure)
    
    print(f"\nExtracted structure:")
    print(f"  Features: {len(structure.features)} items")
    print(f"  Entities: {len(structure.entities)} items")
    print(f"  Flows: {len(structure.flows)} items")
    print(f"  Configuration: {len(structure.configuration)} items")
    print(f"  Error Handling: {len(structure.error_handling)} items")
    print(f"  Testing: {len(structure.testing)} items")
    print(f"  Logging: {len(structure.logging)} items")
    
    print(f"\nQuality warnings ({len(warnings)}):")
    for warning in warnings:
        print(f"  - {warning}")
    
    # Assertions
    assert len(structure.features) > 0, "Should extract features"
    assert len(structure.flows) > 0, "Should extract flows"
    assert len(structure.error_handling) > 0, "Should extract error handling"
    assert len(structure.testing) > 0, "Should extract testing"
    assert len(structure.logging) > 0, "Should extract logging"
    
    # Complete spec should have fewer warnings
    print(f"\n✓ Complete spec has {len(warnings)} warnings (acceptable)")


def test_empty_spec():
    """Test that an empty spec generates all warnings."""
    print("\n=== Test: Empty Spec ===")
    
    prompt = "Just build something."
    
    structure = extract_spec_structure(prompt, "")
    warnings = detect_missing_spec_areas(structure)
    
    print(f"\nQuality warnings ({len(warnings)}):")
    for warning in warnings:
        print(f"  - {warning}")
    
    # Assertions
    assert len(warnings) >= 4, "Should generate multiple warnings for empty spec"
    
    print("✓ Empty spec test passed")


def test_json_serialization():
    """Test that structure can be serialized to JSON."""
    print("\n=== Test: JSON Serialization ===")
    
    prompt = """
    Build a dashboard with user profiles, JWT authentication, and database storage.
    Include logging and error handling.
    """
    
    structure = extract_spec_structure(prompt, "")
    
    # Convert to dict (what API will do)
    structure_dict = structure.model_dump()
    
    # Serialize to JSON
    json_str = json.dumps(structure_dict, indent=2)
    
    print(f"\nSerialized structure:")
    print(json_str)
    
    # Deserialize
    loaded_dict = json.loads(json_str)
    
    # Assertions
    assert 'features' in loaded_dict, "Should have features field"
    assert 'entities' in loaded_dict, "Should have entities field"
    assert isinstance(loaded_dict['features'], list), "Features should be a list"
    
    print("✓ JSON serialization test passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Spec Quality Extraction Tests")
    print("=" * 60)
    
    try:
        test_basic_extraction()
        test_missing_areas_detection()
        test_complete_spec()
        test_empty_spec()
        test_json_serialization()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
