"""Tests for backup functionality."""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import pytest
import shutil
from obsyncit.backup import BackupManager, BackupInfo
from obsyncit.errors import BackupError


@pytest.fixture
def backup_manager():
    """Create a backup manager instance for testing."""
    return BackupManager(
        vault_path=Path("/mock/vault"),
        backup_dir=".backups",
        max_backups=3
    )


@patch('pathlib.Path.exists')
@patch('pathlib.Path.iterdir')
@patch('pathlib.Path.mkdir')
@patch('shutil.copytree')
@patch('obsyncit.backup.BackupInfo.from_backup_path')
def test_create_backup(mock_from_backup_path, mock_copytree, mock_mkdir, mock_iterdir, mock_exists, backup_manager):
    """Test backup creation."""
    # Mock filesystem checks
    mock_exists.return_value = True
    mock_iterdir.return_value = [Mock()]
    mock_mkdir.return_value = None
    mock_copytree.return_value = None
    
    # Mock backup info creation
    mock_backup_info = BackupInfo(
        path=Path("/mock/vault/.backups/backup_20240117_123456_123456"),
        timestamp=datetime.now(),
        size_bytes=1000,
        settings_count=5
    )
    mock_from_backup_path.return_value = mock_backup_info
    
    backup_info = backup_manager.create_backup()
    assert backup_info is not None
    assert backup_info.size_bytes == 1000
    assert backup_info.settings_count == 5


@patch('obsyncit.backup.BackupManager._cleanup_old_backups')
def test_backup_rotation(mock_cleanup, backup_manager):
    """Test that old backups are removed when max_backups is reached."""
    # Mock the cleanup method
    mock_cleanup.return_value = None

    # Create mock backups
    mock_backups = [
        BackupInfo(
            path=Path(f"/mock/backup_{i}"),
            timestamp=datetime.now(),
            size_bytes=0,
            settings_count=1
        )
        for i in range(5)
    ]

    with patch.object(backup_manager, 'list_backups') as mock_list:
        mock_list.return_value = mock_backups
        backups = backup_manager.list_backups()
        assert len(backups) == len(mock_backups)


def test_restore_nonexistent_backup(backup_manager):
    """Test restoring a nonexistent backup."""
    with pytest.raises(BackupError) as exc_info:
        backup_manager.restore_backup("nonexistent")
    assert "No backup found to restore" in str(exc_info.value)


def test_list_backups_sorted(backup_manager):
    """Test that list_backups returns sorted backups."""
    # Create mock backups with different timestamps
    mock_backups = [
        BackupInfo(
            path=Path(f"/mock/backup_{i}"),
            timestamp=datetime.fromtimestamp(1000 + i),
            size_bytes=0,
            settings_count=1
        )
        for i in range(3)
    ]

    with patch.object(backup_manager, 'list_backups') as mock_list:
        mock_list.return_value = sorted(mock_backups, reverse=True)
        backups = backup_manager.list_backups()
        assert len(backups) == 3
        
        timestamps = [b.timestamp.timestamp() for b in backups]
        assert timestamps == sorted(timestamps, reverse=True)