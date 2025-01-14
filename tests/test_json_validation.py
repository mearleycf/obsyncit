"""Tests for JSON validation functionality in ObsidianSettingsSync."""

import json
from pathlib import Path
import pytest
from obsyncit import ObsidianSettingsSync
from obsyncit.schemas import SCHEMA_MAP

@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault structure for testing."""
    vault_path = tmp_path / "test_vault"
    settings_dir = vault_path / ".obsidian"
    settings_dir.mkdir(parents=True)
    return vault_path

@pytest.fixture
def sync_handler(temp_vault):
    """Create a sync handler instance for testing."""
    return ObsidianSettingsSync(
        source_vault=temp_vault,
        target_vault=temp_vault,
        dry_run=True
    )

def test_validate_json_file_valid(sync_handler, tmp_path):
    """Test validation of a valid JSON file."""
    test_file = tmp_path / "valid.json"
    test_data = {"key": "value"}
    
    with open(test_file, 'w') as f:
        json.dump(test_data, f)
    
    assert sync_handler.validate_json_file(test_file) is True

def test_validate_json_file_invalid_json(sync_handler, tmp_path):
    """Test validation of an invalid JSON file."""
    test_file = tmp_path / "invalid.json"
    
    with open(test_file, 'w') as f:
        f.write('{"key": "value",}')  # Invalid JSON (trailing comma)
    
    assert sync_handler.validate_json_file(test_file) is False

def test_validate_json_file_schema_validation(sync_handler, tmp_path):
    """Test schema validation for a known schema type."""
    # Create a test schema for validation
    test_schema = {
        "type": "object",
        "properties": {
            "test": {"type": "string"}
        },
        "required": ["test"]
    }
    
    try:
        # Temporarily add our test schema to SCHEMA_MAP
        SCHEMA_MAP["test_config.json"] = test_schema
        
        # Test valid file
        valid_file = tmp_path / "test_config.json"
        with open(valid_file, 'w') as f:
            json.dump({"test": "value"}, f)
        assert sync_handler.validate_json_file(valid_file) is True
        
        # Test invalid file (missing required field)
        with open(valid_file, 'w') as f:
            json.dump({"wrong_key": "value"}, f)
        assert sync_handler.validate_json_file(valid_file) is False
        
        # Test file with wrong name (should pass as no schema validation)
        other_file = tmp_path / "other.json"
        with open(other_file, 'w') as f:
            json.dump({"wrong_key": "value"}, f)
        assert sync_handler.validate_json_file(other_file) is True
        
    finally:
        # Clean up our test schema
        del SCHEMA_MAP["test_config.json"]

def test_validate_json_file_nonexistent(sync_handler, tmp_path):
    """Test validation of a non-existent file."""
    nonexistent_file = tmp_path / "nonexistent.json"
    assert sync_handler.validate_json_file(nonexistent_file) is True

def test_validate_json_file_permission_error(sync_handler, tmp_path, mocker):
    """Test validation when permission error occurs."""
    test_file = tmp_path / "permission_denied.json"
    
    # Create a valid JSON file
    with open(test_file, 'w') as f:
        json.dump({"key": "value"}, f)
    
    # Mock open to raise PermissionError
    mocker.patch('builtins.open', side_effect=PermissionError)
    
    assert sync_handler.validate_json_file(test_file) is False 