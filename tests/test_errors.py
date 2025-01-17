"""Tests for error handling functionality."""

import os
import errno
import shutil
from pathlib import Path
import pickle
import json
import pytest
from loguru import logger
from obsyncit.errors import (
    ObsyncError, VaultError, ConfigError, ValidationError,
    BackupError, SyncError, handle_file_operation_error, handle_json_error
)


def _safe_cleanup(path):
    """Safe cleanup that handles permission errors."""
    if path.exists():
        try:
            # Try to make writable first
            path.chmod(0o666)
        except OSError:
            pass
        try:
            path.unlink()
        except OSError:
            pass


@pytest.fixture
def test_file(clean_dir):
    """Create a test file for error handling tests."""
    file_path = clean_dir / "test.json"
    file_path.write_text('{"test": true}')
    return file_path


@pytest.fixture
def no_permission_file(clean_dir):
    """Create a file without read/write permissions."""
    file_path = clean_dir / "noperm.json"
    file_path.write_text('{"test": true}')
    file_path.chmod(0o000)  # Remove all permissions
    return file_path


@pytest.fixture
def unreadable_file(clean_dir):
    """Create an unreadable file for testing permission errors."""
    unreadable = clean_dir / "unreadable.txt"
    unreadable.write_text("test content")
    unreadable.chmod(0)
    
    if os.access(str(unreadable), os.R_OK):
        pytest.skip("File was still readable (possibly running in container)")
    
    yield unreadable
    
    # Cleanup: restore permissions so the file can be deleted
    unreadable.chmod(0o644)


@pytest.fixture
def invalid_json_file(clean_dir):
    """Create a file with invalid JSON content."""
    invalid_file = clean_dir / "invalid.json"
    invalid_file.write_text("{invalid json content")
    return invalid_file


def test_base_error():
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
    error = ValidationError(
        "Validation failed",
        path,
        ["Field 'theme' is required", "Invalid type for 'version'"]
    )
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
    error = SyncError(
        "Sync failed",
        source=Path("/source"),
        target=Path("/target"),
        details="Network error"
    )
    expected = (
        "Sync failed\n"
        "Details: Source: /source\n"
        "Target: /target\n"
        "Network error"
    )
    assert str(error) == expected


def test_handle_file_error(clean_dir, unreadable_file):
    """Test handling of file-related errors."""
    # Test file not found error
    test_file = clean_dir / "test.txt"
    with pytest.raises(ObsyncError) as exc_info:
        handle_file_operation_error(FileNotFoundError(), "reading", test_file)
    assert "File not found" in str(exc_info.value)
    assert str(test_file) in str(exc_info.value)

    # Test permission error using unreadable file
    with pytest.raises(ObsyncError) as exc_info:
        handle_file_operation_error(PermissionError(), "reading", unreadable_file)
    assert "Permission denied" in str(exc_info.value)
    assert str(unreadable_file) in str(exc_info.value)

    # Test other file operation error
    nonexistent = clean_dir / "nonexistent.txt"
    with pytest.raises(ObsyncError) as exc_info:
        handle_file_operation_error(OSError("Unknown error"), "reading", nonexistent)
    assert "File operation failed" in str(exc_info.value)
    assert str(nonexistent) in str(exc_info.value)


def test_handle_json_error(clean_dir, invalid_json_file):
    """Test handling of JSON-related errors."""
    # Test JSON decode error with actual invalid JSON file
    try:
        json.loads(invalid_json_file.read_text())
    except json.JSONDecodeError as e:
        with pytest.raises(ValidationError) as exc_info:
            handle_json_error(e, invalid_json_file)
        assert "Invalid JSON format" in str(exc_info.value)
        assert str(invalid_json_file) in str(exc_info.value)


def test_pickle_error():
    """Test error pickling/unpickling."""
    test_path = Path("/test")
    errors = [
        (ObsyncError("Test", "Details"),
         lambda e: (e.message == "Test" and e.details == "Details")),
        
        (VaultError("Test", test_path, "Details"),
         lambda e: (e.vault_path == test_path and "Details" in str(e))),
        
        (ConfigError("Test", test_path, "Details"),
         lambda e: (e.file_path == test_path and "Details" in str(e))),
        
        (ValidationError("Test", test_path, ["Error"]),
         lambda e: (e.file_path == test_path and e.schema_errors == ["Error"])),
        
        (BackupError("Test", test_path, "Details"),
         lambda e: (e.backup_path == test_path and "Details" in str(e))),
        
        (SyncError("Test", test_path, test_path, "Details"),
         lambda e: (e.source == test_path and e.target == test_path))
    ]

    for error, validator in errors:
        unpickled = pickle.loads(pickle.dumps(error))
        assert str(unpickled) == str(error)
        assert validator(unpickled)
