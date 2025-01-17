"""Tests for sync operations in ObsyncIt."""

import json
import os
import shutil
from pathlib import Path
import pytest
from obsyncit.sync import SyncManager, SyncResult
from obsyncit.errors import SyncError, BackupError, ValidationError
from obsyncit.schemas import Config, SyncConfig


@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    return Config()


@pytest.fixture
def source_vault(tmp_path):
    """Create a source vault with sample settings."""
    vault = tmp_path / "source_vault"
    settings = vault / ".obsidian"
    settings.mkdir(parents=True)
    
    # Create sample settings files
    app_json = {
        "promptDelete": False,
        "alwaysUpdateLinks": True
    }
    appearance_json = {
        "accentColor": "",
        "theme": "obsidian"
    }
    hotkeys_json = {
        "editor:toggle-bold": "Ctrl+B"
    }
    core_plugins_json = {
        "file-explorer": True,
        "global-search": True
    }
    community_plugins_json = {
        "dataview": True,
        "templater": True
    }
    
    # Write JSON files
    (settings / "app.json").write_text(json.dumps(app_json))
    (settings / "appearance.json").write_text(json.dumps(appearance_json))
    (settings / "hotkeys.json").write_text(json.dumps(hotkeys_json))
    (settings / "core-plugins.json").write_text(json.dumps(core_plugins_json))
    (settings / "community-plugins.json").write_text(json.dumps(community_plugins_json))
    
    # Create sample themes directory
    themes = settings / "themes"
    themes.mkdir()
    (themes / "theme.css").write_text("/* Sample theme */")
    
    # Create sample snippets directory
    snippets = settings / "snippets"
    snippets.mkdir()
    (snippets / "custom.css").write_text("/* Sample snippet */")
    
    return vault


@pytest.fixture
def target_vault(tmp_path):
    """Create an empty target vault."""
    vault = tmp_path / "target_vault"
    settings = vault / ".obsidian"
    settings.mkdir(parents=True)
    return vault


@pytest.fixture
def sync_manager(source_vault, target_vault, sample_config):
    """Create a sync manager instance for testing."""
    return SyncManager(source_vault, target_vault, sample_config)


@pytest.fixture
def locked_source_settings(sync_manager):
    """Create a source settings directory with no permissions.
    
    Ensures permissions are restored after test, even if it fails.
    """
    settings_dir = sync_manager.source.settings_dir
    settings_dir.chmod(0o000)
    yield settings_dir
    # Cleanup - always restore permissions
    settings_dir.chmod(0o755)


def test_sync_result_validation():
    """Test SyncResult validation."""
    # Valid state - success with no failures
    result = SyncResult(
        success=True,
        items_synced=["app.json"],
        items_failed=[],
        errors={},
    )
    assert result.success
    assert result.any_success

    # Valid state - failure with failed items
    result = SyncResult(
        success=False,
        items_synced=[],
        items_failed=["app.json"],
        errors={"app.json": "error"},
    )
    assert not result.success
    assert not result.any_success

    # Invalid state
    with pytest.raises(ValueError):
        SyncResult(
            success=False,
            items_synced=[],
            items_failed=[],
            errors={},
        )


def test_sync_settings_success(sync_manager):
    """Test successful sync operation."""
    result = sync_manager.sync_settings(["app.json"])
    
    assert isinstance(result, SyncResult)
    assert result.success
    assert "app.json" in result.items_synced
    assert not result.items_failed
    assert not result.errors


def test_sync_settings_partial_failure(sync_manager):
    """Test sync with some failures but ignore_errors enabled."""
    sync_manager.config.sync.ignore_errors = True
    
    # Create invalid JSON to force failure
    (sync_manager.source.settings_dir / "invalid.json").write_text("{invalid}")
    
    result = sync_manager.sync_settings(["app.json", "invalid.json"])
    
    assert isinstance(result, SyncResult)
    assert result.success  # Overall success due to ignore_errors
    assert "app.json" in result.items_synced
    assert "invalid.json" in result.items_failed
    assert "invalid.json" in result.errors


def test_sync_settings_complete_failure(sync_manager, locked_source_settings):
    """Test sync with complete failure."""
    with pytest.raises(SyncError) as exc_info:
        sync_manager.sync_settings()
    assert "Permission denied" in str(exc_info.value)


def test_validate_json_file(sync_manager, source_vault):
    """Test JSON file validation."""
    json_file = source_vault / ".obsidian" / "app.json"
    
    # Valid JSON
    data = sync_manager.validate_json_file(json_file)
    assert isinstance(data, dict)
    assert "promptDelete" in data
    
    # Invalid JSON
    invalid_file = source_vault / ".obsidian" / "invalid.json"
    invalid_file.write_text("{invalid}")
    
    with pytest.raises(ValidationError):
        sync_manager.validate_json_file(invalid_file)
    
    # Missing required fields
    with pytest.raises(ValidationError):
        sync_manager.validate_json_file(
            json_file,
            required_fields=["nonexistent_field"]
        )


def test_sync_with_dry_run(sync_manager):
    """Test sync in dry run mode."""
    sync_manager.config.sync.dry_run = True
    
    result = sync_manager.sync_settings(["app.json"])
    
    assert result.success
    assert not (sync_manager.target.settings_dir / "app.json").exists()


def test_backup_creation(sync_manager):
    """Test backup creation during sync."""
    # Perform initial sync to create some files
    sync_manager.sync_settings(["app.json"])
    
    # Perform another sync which should create backup
    result = sync_manager.sync_settings(["appearance.json"])
    
    assert result.success
    assert len(sync_manager.list_backups()) > 0


def test_restore_backup(sync_manager):
    """Test backup restoration."""
    # Create initial state
    sync_manager.sync_settings(["app.json"])
    original_content = (sync_manager.target.settings_dir / "app.json").read_text()
    
    # Create backup
    sync_manager.backup_mgr.create_backup()
    
    # Modify file
    modified_content = '{"modified": true}'
    (sync_manager.target.settings_dir / "app.json").write_text(modified_content)
    
    # Restore backup
    assert sync_manager.restore_backup()
    
    # Verify restoration
    restored_content = (sync_manager.target.settings_dir / "app.json").read_text()
    assert restored_content == original_content


def test_sync_empty_items_list(sync_manager):
    """Test syncing with empty items list."""
    result = sync_manager.sync_settings([])
    assert isinstance(result, SyncResult)
    assert result.success
    assert not result.items_synced