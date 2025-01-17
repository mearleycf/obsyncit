"""Tests for backup functionality."""

import os
import shutil
import time
from pathlib import Path
import pytest
from obsyncit.backup import BackupManager
from obsyncit.errors import BackupError


def cleanup_vault(path):
    """Cleanup vault directory by restoring permissions and removing files."""
    try:
        if not path.exists():
            return
        if path.is_file():
            os.chmod(path, 0o644)
            path.unlink()
        else:
            for item in path.iterdir():
                cleanup_vault(item)
            os.chmod(path, 0o755)
            path.rmdir()
    except (PermissionError, FileNotFoundError):
        pass


@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault directory with sample settings."""
    vault = tmp_path / "test_vault"
    vault.mkdir()
    settings = vault / ".obsidian"
    settings.mkdir()
    
    # Create some test files
    test_file = settings / "test.json"
    test_file.write_text('{"test": "data"}')
    
    yield vault
    cleanup_vault(vault)


@pytest.fixture
def backup_manager(temp_vault):
    """Create a backup manager instance for testing."""
    return BackupManager(
        vault_path=temp_vault,
        backup_dir=".backups",
        max_backups=3
    )


def restore_permissions(path: Path):
    """Recursively restore permissions on a path and its contents."""
    try:
        if not path.exists():
            return
        if path.is_file():
            path.chmod(0o644)
        else:
            for item in path.iterdir():
                restore_permissions(item)
            path.chmod(0o755)
    except (PermissionError, FileNotFoundError):
        pass  # Ignore errors during cleanup


@pytest.fixture
def locked_settings_dir(temp_vault):
    """Create a settings directory with no permissions."""
    settings_dir = temp_vault / ".obsidian"
    settings_dir.chmod(0o000)
    return settings_dir


def test_create_backup(backup_manager, temp_vault):
    """Test backup creation."""
    # Create backup
    backup_info = backup_manager.create_backup()
    assert backup_info is not None
    assert backup_info.path.exists()

    # Verify backup contains settings
    backup_settings = backup_info.path / ".obsidian"
    assert backup_settings.exists()
    assert (backup_settings / "test.json").exists()
    assert (backup_settings / "test.json").read_text() == '{"test": "data"}'


def test_backup_rotation(backup_manager, temp_vault):
    """Test that old backups are removed when max_backups is reached."""
    # Create more than max_backups
    created_backups = []
    for _ in range(5):
        backup = backup_manager.create_backup()
        assert backup is not None
        created_backups.append(backup)
        time.sleep(0.1)  # Ensure unique timestamps

    # Verify only max_backups are kept
    backups = backup_manager.list_backups()
    assert len(backups) == backup_manager.max_backups

    # Verify backups are sorted by date (newest first)
    backup_times = [b.timestamp.timestamp() for b in backups]  # Convert to Unix timestamps
    assert backup_times == sorted(backup_times, reverse=True)


def test_restore_latest_backup(backup_manager, temp_vault):
    """Test restoring the latest backup."""
    # Get initial settings path
    settings_dir = temp_vault / ".obsidian"
    test_file = settings_dir / "test.json"

    # Create backup of original content
    backup_path = backup_manager.create_backup()
    assert backup_path is not None

    # Modify file
    test_file.write_text('{"test": "modified"}')

    # Restore backup
    restored_path = backup_manager.restore_backup()
    assert restored_path is not None

    # Verify file was restored
    assert test_file.read_text() == '{"test": "data"}'


def test_restore_specific_backup(backup_manager, temp_vault):
    """Test restoring a specific backup."""
    # Get settings path
    settings_dir = temp_vault / ".obsidian"
    test_file = settings_dir / "test.json"

    # Create first backup
    backup1 = backup_manager.create_backup()
    assert backup1 is not None
    backup1_path = backup1.path  # Store the path from BackupInfo
    time.sleep(0.1)

    # Create second backup with different content
    test_file.write_text('{"test": "version2"}')
    backup2 = backup_manager.create_backup()
    assert backup2 is not None
    time.sleep(0.1)

    # Modify file again
    test_file.write_text('{"test": "version3"}')

    # Restore first backup
    restored_path = backup_manager.restore_backup(backup1_path)  # Use the path instead of BackupInfo
    assert restored_path is not None

    # Verify correct version was restored
    assert test_file.read_text() == '{"test": "data"}'


def test_restore_nonexistent_backup(backup_manager, temp_vault):
    """Test restoring a nonexistent backup."""
    nonexistent = temp_vault / ".backups" / "nonexistent"
    with pytest.raises(BackupError) as exc_info:
        backup_manager.restore_backup(nonexistent)
    assert "No backup found to restore" in str(exc_info.value)


def test_backup_with_no_settings(backup_manager, temp_vault):
    """Test backup creation when settings directory is empty."""
    # Remove settings directory
    shutil.rmtree(temp_vault / ".obsidian")
    os.mkdir(temp_vault / ".obsidian")

    # Attempt backup - should return None for empty settings
    backup_path = backup_manager.create_backup()
    assert backup_path is None


def test_backup_permission_error(backup_manager, locked_settings_dir):
    """Test backup with permission error."""
    # Attempt backup
    with pytest.raises(BackupError) as exc_info:
        backup_manager.create_backup()
    assert "Permission denied" in str(exc_info.value)


def test_list_backups_sorted(backup_manager, temp_vault):
    """Test that list_backups returns sorted backups."""
    # Create multiple backups
    created_backups = []
    for _ in range(3):
        backup = backup_manager.create_backup()
        assert backup is not None
        created_backups.append(str(backup))
        time.sleep(0.1)

    # Get list of backups
    listed_backups = backup_manager.list_backups()

    # Verify all created backups are listed
    assert len(listed_backups) == len(created_backups)
    
    # Verify backups are sorted (newest first)
    assert listed_backups == sorted(listed_backups, reverse=True)