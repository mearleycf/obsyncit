"""Tests for JSON schema validation functionality."""

import json
from pathlib import Path
import pytest
from obsyncit.sync import SyncManager
from obsyncit.schemas import Config, SyncConfig
from obsyncit.errors import ValidationError, ObsyncError
from unittest.mock import Mock


@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault directory."""
    vault = tmp_path / "test_vault"
    vault.mkdir()
    settings = vault / ".obsidian"
    settings.mkdir()
    return vault


@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    config = Config(
        sync=SyncConfig(
            core_settings=True,
            core_plugins=True,
            community_plugins=True,
            themes=True,
            snippets=True,
            dry_run=True
        )
    )
    return config


@pytest.fixture
def sync_handler(temp_vault, sample_config):
    """Create a sync handler instance for testing."""
    return SyncManager(
        source_vault=str(temp_vault),
        target_vault=str(temp_vault),
        config=sample_config
    )


@pytest.fixture
def sync_manager(tmp_path):
    """Create a sync manager instance for testing."""
    source_vault = tmp_path / "source"
    target_vault = tmp_path / "target"
    source_vault.mkdir()
    target_vault.mkdir()
    config = Config()
    return SyncManager(source_vault, target_vault, config)


def test_validate_json_file_valid(sync_manager, tmp_path):
    """Test validation of a valid JSON file."""
    test_file = tmp_path / "test.json"
    test_file.write_text('{"valid": "json"}')
    
    # Should not raise any exceptions
    sync_manager.validate_json_file(test_file)


def test_validate_json_file_invalid_json(sync_manager, tmp_path):
    """Test validation of an invalid JSON file."""
    test_file = tmp_path / "invalid.json"
    test_file.write_text('{"invalid": json}')  # Missing quotes
    
    with pytest.raises(ValidationError, match="Invalid JSON"):
        sync_manager.validate_json_file(test_file)


def test_validate_json_file_schema_validation(sync_manager, tmp_path):
    """Test JSON schema validation."""
    test_file = tmp_path / "schema.json"
    test_file.write_text('{"invalid": "schema"}')
    
    with pytest.raises(ValidationError, match="Schema validation failed"):
        sync_manager.validate_json_file(test_file, required_fields=["missing_field"])


def test_validate_json_file_nonexistent(sync_manager, tmp_path):
    """Test validation of a nonexistent file."""
    test_file = tmp_path / "nonexistent.json"
    
    with pytest.raises(ObsyncError, match="File not found"):
        sync_manager.validate_json_file(test_file)


def test_validate_json_file_permission_error(sync_manager, tmp_path):
    """Test validation with permission error."""
    test_file = tmp_path / "noperm.json"
    test_file.write_text('{"valid": "json"}')
    test_file.chmod(0o000)  # Remove all permissions
    
    with pytest.raises(ObsyncError, match="Permission denied"):
        sync_manager.validate_json_file(test_file)

    # Cleanup: restore permissions for cleanup
    test_file.chmod(0o644) 