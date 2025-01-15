"""Tests for backup functionality."""

import os
import shutil
import time
from pathlib import Path
import pytest
from obsyncit.backup import BackupManager
from obsyncit.errors import BackupError


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
    
    return vault


@pytest.fixture
def backup_manager(temp_vault):
    """Create a backup manager instance for testing."""
    return BackupManager(
        vault_path=temp_vault,
        backup_dir=".backups",
        max_backups=3
    )


def test_create_backup(backup_manager, temp_vault):
    """Test backup creation."""
    # Create backup
    backup_path = backup_manager.create_backup()
    assert backup_path is not None
    assert backup_path.exists()
    assert backup_path.is_dir()

    # Verify backup contains settings
    backup_settings = backup_path / ".obsidian"
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
    backup_times = [int(p.split("_")[-1]) for p in backups]
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
    time.sleep(0.1)

    # Create second backup with different content
    test_file.write_text('{"test": "version2"}')
    backup2 = backup_manager.create_backup()
    assert backup2 is not None
    time.sleep(0.1)

    # Modify file again
    test_file.write_text('{"test": "version3"}')

    # Restore first backup
    restored_path = backup_manager.restore_backup(backup1)
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
    """
    Test backup creation when settings directory is empty.
    
    This test verifies that the backup manager gracefully handles cases where:
    1. The .obsidian directory exists but is empty
    2. No settings files are present to backup
    
    Expected behavior: Returns None instead of creating an empty backup
    """
    # Remove settings directory
    shutil.rmtree(temp_vault / ".obsidian")
    os.mkdir(temp_vault / ".obsidian")

    # Attempt backup - should return None for empty settings
    backup_path = backup_manager.create_backup()
    assert backup_path is None


@pytest.mark.parametrize("permission_scenario", [
    ("no_read", 0o000, "Permission denied reading source"),
    ("no_write_backup", 0o444, "Permission denied creating backup"),
    ("no_execute", 0o666, "Permission denied accessing directory"),
])
def test_backup_permission_scenarios(backup_manager, temp_vault, permission_scenario):
    """
    Test backup operations under different permission scenarios.
    
    Tests various permission combinations that might occur in real environments:
    - No read access to source
    - No write access to backup location
    - No execute permission for directory traversal
    """
    scenario_name, permission, expected_error = permission_scenario
    settings_dir = temp_vault / ".obsidian"
    
    if scenario_name == "no_write_backup":
        # Test backup directory permissions
        backup_dir = temp_vault / ".backups"
        backup_dir.mkdir(exist_ok=True)
        backup_dir.chmod(permission)
    else:
        # Test source directory permissions
        settings_dir.chmod(permission)

    # Attempt backup
    with pytest.raises(BackupError) as exc_info:
        backup_manager.create_backup()
    assert expected_error in str(exc_info.value)

    # Cleanup - restore permissions
    if scenario_name == "no_write_backup":
        backup_dir.chmod(0o755)
    else:
        settings_dir.chmod(0o755)


def test_backup_mixed_permissions(backup_manager, temp_vault):
    """
    Test backup behavior with mixed permission settings.
    
    Verifies backup operations when:
    - Some files are readable but others aren't
    - Some directories are accessible but others aren't
    This reflects real-world scenarios where permissions vary across the vault.
    """
    settings_dir = temp_vault / ".obsidian"
    
    # Create additional test files with different permissions
    restricted_file = settings_dir / "restricted.json"
    restricted_file.write_text('{"restricted": true}')
    restricted_file.chmod(0o000)
    
    readable_file = settings_dir / "readable.json"
    readable_file.write_text('{"readable": true}')
    
    with pytest.raises(BackupError) as exc_info:
        backup_manager.create_backup()
    assert "Permission denied" in str(exc_info.value)
    
    # Cleanup
    restricted_file.chmod(0o644)


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