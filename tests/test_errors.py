"""Tests for error handling functionality."""

import os
from pathlib import Path
import pickle
import json
import pytest
from loguru import logger
from obsyncit.errors import (
    ObsyncError, VaultError, ConfigError, ValidationError,
    BackupError, SyncError, handle_file_operation_error, handle_json_error
)


@pytest.fixture(autouse=True)
def setup_logging(caplog):
    """Configure logging for tests."""
    handler_id = logger.add(caplog.handler, format="{message}")
    yield
    logger.remove(handler_id)


@pytest.fixture
def test_file(tmp_path):
    """Create a test file for file operations."""
    file_path = tmp_path / "test.json"
    file_path.write_text('{"test": "data"}')
    yield file_path
    # Cleanup - ensure file is writable for deletion
    if file_path.exists():
        file_path.chmod(0o644)


def test_obsync_error():
    """Test base error functionality."""
    error = ObsyncError("Test error")
    assert str(error) == "Test error"

    error_with_details = ObsyncError("Test error", "Additional info")
    # Check essential components
    assert "Test error" in str(error_with_details)
    assert "Additional info" in str(error_with_details)


def test_vault_error(tmp_path):
    """Test VaultError functionality."""
    path = tmp_path / "test_vault"
    error = VaultError("Invalid vault", vault_path=path)
    
    # Check essential components
    assert "Invalid vault" in str(error)
    assert str(path) in str(error)
    assert "Details: Vault:" in str(error)

    # Test with additional details
    error_with_details = VaultError("Invalid vault", vault_path=path, details="Not readable")
    assert "Invalid vault" in str(error_with_details)
    assert str(path) in str(error_with_details)
    assert "Not readable" in str(error_with_details)


def test_config_error(tmp_path):
    """Test ConfigError functionality."""
    path = tmp_path / "config.toml"
    error = ConfigError("Invalid config", file_path=path, details="Missing field")
    
    # Check essential components
    assert "Invalid config" in str(error)
    assert str(path) in str(error)
    assert "Missing field" in str(error)
    assert "Details: Config:" in str(error)


def test_validation_error(tmp_path):
    """Test ValidationError functionality."""
    path = tmp_path / "test.json"
    errors = ["Field 'theme' is required", "Invalid type for 'version'"]
    error = ValidationError("Validation failed", path, errors)
    
    # Check essential components
    assert "Validation failed" in str(error)
    assert str(path) in str(error)
    assert "Details: File:" in str(error)
    # Verify each error message is present
    for err in errors:
        assert err in str(error)


def test_backup_error(tmp_path):
    """Test BackupError functionality."""
    path = tmp_path / "backup"
    error = BackupError("Backup failed", backup_path=path, details="Disk full")
    
    # Check essential components
    assert "Backup failed" in str(error)
    assert str(path) in str(error)
    assert "Disk full" in str(error)
    assert "Details: Backup:" in str(error)


def test_sync_error(tmp_path):
    """Test SyncError functionality."""
    source = tmp_path / "source"
    target = tmp_path / "target"
    error = SyncError(
        "Sync failed",
        source=source,
        target=target,
        details="Network error"
    )
    
    # Check essential components
    assert "Sync failed" in str(error)
    assert str(source) in str(error)
    assert str(target) in str(error)
    assert "Network error" in str(error)
    assert "Details: Source:" in str(error)
    assert "Target:" in str(error)


def test_handle_file_operation_error(test_file, caplog):
    """Test file operation error handler."""
    # Test permission error
    test_file.chmod(0o000)
    try:
        with open(test_file, 'r') as f:
            f.read()
    except PermissionError as e:
        handle_file_operation_error(e, "reading", test_file)
    assert "Permission denied reading" in caplog.text
    assert str(test_file) in caplog.text
    caplog.clear()

    # Test file not found error
    nonexistent = test_file.parent / "nonexistent.json"
    try:
        with open(nonexistent, 'r') as f:
            f.read()
    except FileNotFoundError as e:
        handle_file_operation_error(e, "reading", nonexistent)
    assert "File not found:" in caplog.text
    assert str(nonexistent) in caplog.text


def test_handle_json_error(test_file, caplog):
    """Test JSON error handler."""
    # Write invalid JSON
    test_file.write_text('{"invalid": json, missing: quotes}')

    try:
        with open(test_file) as f:
            json.load(f)
    except json.JSONDecodeError as e:
        handle_json_error(e, test_file)

    # Verify error details are logged
    assert "Invalid JSON in" in caplog.text
    assert str(test_file) in caplog.text
    assert "Line" in caplog.text
    assert "Column" in caplog.text
    assert "Context:" in caplog.text


def test_error_pickling(tmp_path):
    """Test that errors can be pickled/unpickled."""
    # Create test paths using tmp_path
    test_paths = {
        'vault': tmp_path / "test_vault",
        'config': tmp_path / "test.toml",
        'json': tmp_path / "test.json",
        'backup': tmp_path / "backup",
        'source': tmp_path / "source",
        'target': tmp_path / "target"
    }
    
    errors = [
        ObsyncError("Test error", "Details"),
        VaultError("Test error", vault_path=test_paths['vault'], details="Not readable"),
        ConfigError("Test error", file_path=test_paths['config'], details="Missing field"),
        ValidationError("Test error", test_paths['json'], ["Error 1", "Error 2"]),
        BackupError("Test error", backup_path=test_paths['backup'], details="Disk full"),
        SyncError("Test error", source=test_paths['source'], target=test_paths['target'], details="Network error")
    ]

    for error in errors:
        # Pickle and unpickle
        pickled = pickle.dumps(error)
        unpickled = pickle.loads(pickled)
        
        # Verify message and details are preserved
        assert unpickled.message == error.message
        
        # Verify error-specific attributes using string comparison for paths
        if isinstance(error, VaultError):
            assert str(unpickled.vault_path) == str(error.vault_path)
        elif isinstance(error, ConfigError):
            assert str(unpickled.file_path) == str(error.file_path)
        elif isinstance(error, ValidationError):
            assert str(unpickled.file_path) == str(error.file_path)
            assert unpickled.schema_errors == error.schema_errors
        elif isinstance(error, BackupError):
            assert str(unpickled.backup_path) == str(error.backup_path)
        elif isinstance(error, SyncError):
            assert str(unpickled.source) == str(error.source)
            assert str(unpickled.target) == str(error.target) 