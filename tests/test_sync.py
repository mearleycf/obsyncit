"""Tests for syncing functionality."""

import json
from pathlib import Path
import pytest
from obsyncit.sync import SyncManager, SyncResult
from obsyncit.schemas import Config, SyncConfig
from obsyncit.errors import SyncError, ValidationError
from tests.test_utils import create_test_vault


@pytest.fixture
def sample_vaults(clean_dir):
    """Create sample source and target vaults for testing."""
    source_vault = create_test_vault(clean_dir / "source_vault")
    target_vault = create_test_vault(clean_dir / "target_vault")  # Create with default settings
    return source_vault, target_vault


@pytest.fixture
def sync_manager(sample_vaults):
    """Create a sync manager with test configuration."""
    source_vault, target_vault = sample_vaults
    config = Config()
    config.sync.dry_run = False
    config.sync.ignore_errors = False
    return SyncManager(source_vault, target_vault, config)


def test_sync_settings_success(sync_manager):
    """Test successful sync operation."""
    # Source and target vaults already have app.json with default settings
    result = sync_manager.sync_settings(["app.json"])

    assert result.success
    assert len(result.items_synced) == 1
    assert not result.items_failed
    assert not result.errors


def test_sync_settings_complete_failure(sync_manager):
    """Test sync with complete failure."""
    # Create invalid JSON to force failure
    invalid_json = sync_manager.source.settings_dir / "app.json"  # Use a core settings file name
    invalid_json.write_text("{invalid")

    # Ensure the file exists and has invalid content
    assert invalid_json.exists()
    assert invalid_json.read_text() == "{invalid"

    # Disable ignore_errors to ensure the error is raised
    sync_manager.config.sync.ignore_errors = False
    sync_manager.config.sync.core_settings = True  # Enable core settings sync

    # Attempt to sync the invalid file
    with pytest.raises(ValidationError) as exc_info:
        sync_manager.sync_settings(["app.json"])
    
    # Verify the error message
    assert "Invalid JSON" in str(exc_info.value)


def test_sync_with_dry_run(sync_manager):
    """Test sync in dry run mode."""
    sync_manager.config.sync.dry_run = True

    # First change target content to be different from source
    target_file = sync_manager.target.settings_dir / "app.json"
    target_file.write_text('{"test": false}')

    result = sync_manager.sync_settings(["app.json"])
    assert result.success
    assert len(result.items_synced) == 1

    # Verify file wasn't synced (still has old content)
    assert json.loads(target_file.read_text())["test"] is False


def test_backup_creation(sync_manager):
    """Test backup creation during sync."""
    # Modify target file to be different from source
    target_file = sync_manager.target.settings_dir / "app.json"
    target_file.write_text('{"test": false}')

    # Sync should backup the modified target and then sync source content
    sync_manager.sync_settings(["app.json"])

    # Check backup exists and contains old content
    backup_dir = sync_manager.target.vault_path / ".backups"
    assert backup_dir.exists()
    backup_files = list(backup_dir.rglob("app.json"))
    assert len(backup_files) > 0
    assert json.loads(backup_files[0].read_text())["test"] is False

    # Verify target has been synced with source content
    assert json.loads(target_file.read_text())["test"] is True


def test_restore_backup(sync_manager, sample_vaults):
    """Test backup restoration."""
    source_vault, _ = sample_vaults
    target_file = sync_manager.target.settings_dir / "app.json"

    # Get original content
    original_content = target_file.read_text()

    # Create a backup with current content
    backup = sync_manager.backup_mgr.create_backup()
    assert backup is not None

    # Modify target content
    target_file.write_text('{"test": false}')

    # Restore backup
    restored = sync_manager.backup_mgr.restore_backup()
    assert restored is not None

    # Verify content restored
    assert target_file.read_text() == original_content


def test_sync_empty_items_list(sync_manager):
    """Test syncing with empty items list."""
    result = sync_manager.sync_settings([])
    assert result.success
    assert len(result.items_synced) == 0
    assert len(result.items_failed) == 0
    assert not result.errors