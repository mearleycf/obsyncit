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
    assert str(error_with_details) == "Test error\nDetails: Additional info"


def test_vault_error():
    """Test VaultError functionality."""
    path = Path("/test/path")
    error = VaultError("Invalid vault", vault_path=path)
    expected = "Invalid vault\nDetails: Vault: /test/path"
    assert str(error) == expected

    # Test with additional details
    error_with_details = VaultError("Invalid vault", vault_path=path, details="Not readable")
    expected = "Invalid vault\nDetails: Vault: /test/path\nNot readable"
    assert str(error_with_details) == expected


def test_config_error():
    """Test ConfigError functionality."""
    path = Path("/test/config.toml")
    error = ConfigError("Invalid config", file_path=path, details="Missing field")
    expected = "Invalid config\nDetails: Config: /test/config.toml\nMissing field"
    assert str(error) == expected


def test_validation_error():
    """Test ValidationError functionality."""
    path = Path("/test/file.json")
    errors = ["Field 'theme' is required", "Invalid type for 'version'"]
    error = ValidationError("Validation failed", path, errors)
    expected = (
        "Validation failed\n"
        "Details: File: /test/file.json\n"
        "- Field 'theme' is required\n"
        "- Invalid type for 'version'"
    )
    assert str(error) == expected


def test_backup_error():
    """Test BackupError functionality."""
    path = Path("/test/backup")
    error = BackupError("Backup failed", backup_path=path, details="Disk full")
    expected = "Backup failed\nDetails: Backup: /test/backup\nDisk full"
    assert str(error) == expected


def test_sync_error():
    """Test SyncError functionality."""
    source = Path("/source")
    target = Path("/target")
    error = SyncError(
        "Sync failed",
        source=source,
        target=target,
        details="Network error"
    )
    expected = (
        "Sync failed\n"
        "Details: Source: /source\n"
        "Target: /target\n"
        "Network error"
    )
    assert str(error) == expected


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


def test_error_pickling():
    """Test that errors can be pickled/unpickled."""
    errors = [
        ObsyncError("Test error", "Details"),
        VaultError("Test error", vault_path=Path("/test"), details="Not readable"),
        ConfigError("Test error", file_path=Path("/test.toml"), details="Missing field"),
        ValidationError("Test error", Path("/test.json"), ["Error 1", "Error 2"]),
        BackupError("Test error", backup_path=Path("/backup"), details="Disk full"),
        SyncError("Test error", source=Path("/src"), target=Path("/dst"), details="Network error")
    ]

    for error in errors:
        # Pickle and unpickle
        pickled = pickle.dumps(error)
        unpickled = pickle.loads(pickled)
        
        # Verify all attributes are preserved
        assert str(unpickled) == str(error)
        assert unpickled.message == error.message
        
        # Verify error-specific attributes
        if isinstance(error, VaultError):
            assert unpickled.vault_path == error.vault_path
        elif isinstance(error, ConfigError):
            assert unpickled.file_path == error.file_path
        elif isinstance(error, ValidationError):
            assert unpickled.file_path == error.file_path
            assert unpickled.schema_errors == error.schema_errors
        elif isinstance(error, BackupError):
            assert unpickled.backup_path == error.backup_path
        elif isinstance(error, SyncError):
            assert unpickled.source == error.source
            assert unpickled.target == error.target 