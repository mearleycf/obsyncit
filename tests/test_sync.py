"""Tests for sync operations in ObsyncIt."""

import json
import os
import shutil
from pathlib import Path
import pytest
from obsyncit.sync import SyncManager
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
    """Create a sync manager instance."""
    return SyncManager(source_vault, target_vault, sample_config)


def test_sync_all_settings(sync_manager, source_vault, target_vault):
    """Test syncing all settings from source to target."""
    # Perform sync
    assert sync_manager.sync_settings() is True
    
    # Verify files were synced
    source_files = list((source_vault / ".obsidian").glob("**/*"))
    target_files = list((target_vault / ".obsidian").glob("**/*"))
    assert len(source_files) == len(target_files)
    
    # Check content of synced files
    app_json = json.loads((target_vault / ".obsidian" / "app.json").read_text())
    assert app_json["promptDelete"] is False
    assert app_json["alwaysUpdateLinks"] is True


def test_sync_specific_items(sync_manager, source_vault, target_vault):
    """Test syncing specific settings items."""
    # Sync only appearance and themes
    items = ["appearance.json", "themes"]
    assert sync_manager.sync_settings(items) is True
    
    # Verify only specified files were synced
    target_settings = target_vault / ".obsidian"
    assert (target_settings / "appearance.json").exists()
    assert (target_settings / "themes").exists()
    assert not (target_settings / "app.json").exists()


def test_sync_dry_run(source_vault, target_vault, sample_config):
    """Test dry run mode doesn't modify files."""
    # Create sync manager in dry run mode
    sample_config.sync.dry_run = True
    sync_manager = SyncManager(source_vault, target_vault, sample_config)
    
    # Perform sync
    assert sync_manager.sync_settings() is True
    
    # Verify no files were created
    target_files = list((target_vault / ".obsidian").glob("**/*"))
    assert len(target_files) == 0


def test_sync_invalid_source_vault(target_vault, sample_config):
    """Test syncing with invalid source vault."""
    sync_manager = SyncManager(Path("/nonexistent"), target_vault, sample_config)
    with pytest.raises(SyncError) as exc_info:
        sync_manager.sync_settings()
    assert "Vault directory does not exist" in str(exc_info.value)


def test_sync_invalid_target_vault(source_vault, sample_config):
    """Test syncing with invalid target vault."""
    sync_manager = SyncManager(source_vault, Path("/nonexistent"), sample_config)
    with pytest.raises(SyncError) as exc_info:
        sync_manager.sync_settings()
    assert "Vault directory does not exist" in str(exc_info.value)


def test_sync_with_backup_failure(sync_manager, source_vault, target_vault, monkeypatch):
    """Test sync behavior when backup fails."""
    def mock_create_backup(*args):
        raise BackupError("Backup failed", backup_path=target_vault / ".backups")
    
    monkeypatch.setattr(sync_manager.backup_mgr, "create_backup", mock_create_backup)
    
    with pytest.raises(BackupError) as exc_info:
        sync_manager.sync_settings()
    assert "Backup failed" in str(exc_info.value)


def test_sync_with_invalid_json(sync_manager, source_vault, target_vault):
    """Test sync behavior with invalid JSON files."""
    # Create invalid JSON in source
    invalid_json = source_vault / ".obsidian" / "app.json"
    invalid_json.write_text("{invalid json}")
    
    with pytest.raises(ValidationError) as exc_info:
        sync_manager.sync_settings()
    assert "Invalid JSON" in str(exc_info.value)


def test_sync_with_permission_error(sync_manager, source_vault, target_vault):
    """Test sync behavior with permission errors."""
    # Create a file in the source vault
    source_settings = source_vault / ".obsidian"
    target_settings = target_vault / ".obsidian"
    
    # Create a test file in the source
    test_file = source_settings / "test.json"
    test_file.write_text('{"test": true}')
    
    # Remove write permissions from target settings dir
    target_settings.chmod(0o444)  # Read-only
    
    with pytest.raises(SyncError) as exc_info:
        sync_manager.sync_settings(["test.json"])
    assert "Permission denied" in str(exc_info.value)
    
    # Cleanup - restore permissions for cleanup
    target_settings.chmod(0o755)


def test_sync_empty_items_list(sync_manager):
    """Test syncing with empty items list."""
    assert sync_manager.sync_settings([]) is True


def test_sync_ignore_errors(source_vault, target_vault, sample_config):
    """Test sync with ignore_errors enabled."""
    # Enable error ignoring
    sample_config.sync.ignore_errors = True
    sync_manager = SyncManager(source_vault, target_vault, sample_config)
    
    # Create invalid JSON to trigger error
    invalid_json = source_vault / ".obsidian" / "app.json"
    invalid_json.write_text("{invalid json}")
    
    # Create a valid file to ensure partial success
    valid_json = source_vault / ".obsidian" / "appearance.json"
    valid_json.write_text('{"theme": "light"}')
    
    # Sync should complete despite error
    assert sync_manager.sync_settings(["app.json", "appearance.json"]) is True
    
    # Verify valid file was synced
    target_appearance = target_vault / ".obsidian" / "appearance.json"
    assert target_appearance.exists()
    assert json.loads(target_appearance.read_text())["theme"] == "light" 