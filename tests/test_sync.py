"""Tests for sync operations in ObsyncIt."""

import json
import shutil
from pathlib import Path
import pytest
from obsyncit.sync import SyncManager
from obsyncit.errors import SyncError, BackupError, ValidationError
from obsyncit.schemas import Config, SyncConfig

@pytest.fixture

def sample_config():
    """Create a sample configuration for testing."""
    config = Config()
    config.sync.dry_run = False
    config.sync.ignore_errors = False
    config.sync.backup_enabled = True
    return config
@pytest.fixture
def source_vault(tmp_path):
    """Create a source vault with sample settings."""
    vault = tmp_path / "source_vault"
    settings = vault / ".obsidian"
    settings.mkdir(parents=True)
    
    # Create sample settings files
    settings_data = {
        "app.json": {
            "promptDelete": False,
            "alwaysUpdateLinks": True
        },
        "appearance.json": {
            "accentColor": "",
            "theme": "obsidian"
        },
        "hotkeys.json": {
            "editor:toggle-bold": "Ctrl+B"
        },
        "core-plugins.json": {
            "file-explorer": True,
            "global-search": True
        },
        "community-plugins.json": {
            "dataview": True,
            "templater": True
        }
    }
    
    # Write JSON files
    for filename, data in settings_data.items():
        (settings / filename).write_text(json.dumps(data))
    
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


@pytest.mark.parametrize("items,expected_files", [
    (["appearance.json", "themes"], {"appearance.json", "themes"}),
    (["app.json", "hotkeys.json"], {"app.json", "hotkeys.json"}),
    (["community-plugins.json", "snippets"], {"community-plugins.json", "snippets"}),
])
def test_sync_specific_items(sync_manager, source_vault, target_vault, items, expected_files):
    """Test syncing specific settings items."""
    assert sync_manager.sync_settings(items) is True
    
    # Verify only specified files were synced
    target_settings = target_vault / ".obsidian"
    for file in expected_files:
        assert (target_settings / file).exists()
    
    # Verify other files were not synced
    all_possible_files = {"app.json", "appearance.json", "hotkeys.json", 
                         "core-plugins.json", "community-plugins.json", 
                         "themes", "snippets"}
    for file in all_possible_files - expected_files:
        assert not (target_settings / file).exists()


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


@pytest.mark.parametrize("vault_type,create_vault", [
    ("source", False),
    ("target", False),
    ("source", True),  # Test with empty vault
    ("target", True),  # Test with empty vault
])
def test_sync_invalid_vault(tmp_path, sample_config, vault_type, create_vault):
    """Test syncing with invalid vault configurations."""
    # Create the valid vault
    valid_vault = tmp_path / "valid_vault"
    valid_vault.mkdir()
    (valid_vault / ".obsidian").mkdir()

    # Set up the invalid vault
    invalid_vault = tmp_path / "invalid_vault"
    if create_vault:
        invalid_vault.mkdir()  # Create empty vault without .obsidian directory

    # Create sync manager based on which vault is invalid
    if vault_type == "source":
        sync_manager = SyncManager(invalid_vault, valid_vault, sample_config)
    else:
        sync_manager = SyncManager(valid_vault, invalid_vault, sample_config)

    with pytest.raises(SyncError) as exc_info:
        sync_manager.sync_settings()
    assert "Invalid vault" in str(exc_info.value)


def test_sync_with_backup_failure(sync_manager, source_vault, target_vault, monkeypatch):
    """Test sync behavior when backup fails."""
    def mock_create_backup(*args):
        raise BackupError("Backup failed", backup_path=target_vault / ".backups")
    
    monkeypatch.setattr(sync_manager.backup_mgr, "create_backup", mock_create_backup)
    
    with pytest.raises(BackupError) as exc_info:
        sync_manager.sync_settings()
    assert "Backup failed" in str(exc_info.value)


@pytest.mark.parametrize("invalid_content,error_message", [
    ("{invalid json}", "Invalid JSON"),
    ('{"missing": "comma" "key": "value"}', "Invalid JSON"),
    ("not json at all", "Invalid JSON"),
])
def test_sync_with_invalid_json(sync_manager, source_vault, target_vault, invalid_content, error_message):
    """Test sync behavior with various invalid JSON content."""
    # Create invalid JSON in source
    invalid_json = source_vault / ".obsidian" / "app.json"
    invalid_json.write_text(invalid_content)
    
    with pytest.raises(ValidationError) as exc_info:
        sync_manager.sync_settings()
    assert error_message in str(exc_info.value)


@pytest.mark.parametrize("permission,expected_error", [
    (0o444, "Permission denied"),  # Read-only
    (0o000, "Permission denied"),  # No permissions
])
def test_sync_with_permission_error(sync_manager, source_vault, target_vault, permission, expected_error):
    """Test sync behavior with different permission configurations."""
    # Create a test file in the source
    source_settings = source_vault / ".obsidian"
    target_settings = target_vault / ".obsidian"
    test_file = source_settings / "test.json"
    test_file.write_text('{"test": true}')
    
    # Modify permissions
    target_settings.chmod(permission)
    
    with pytest.raises(SyncError) as exc_info:
        sync_manager.sync_settings(["test.json"])
    assert expected_error in str(exc_info.value)
    
    # Cleanup - restore permissions for cleanup
    target_settings.chmod(0o755)


def test_sync_empty_items_list(sync_manager):
    """Test syncing with empty items list."""
    assert sync_manager.sync_settings([]) is True


@pytest.mark.parametrize("invalid_file,valid_file,valid_content", [
    ("app.json", "appearance.json", {"theme": "light"}),
    ("hotkeys.json", "core-plugins.json", {"file-explorer": True}),
])
def test_sync_ignore_errors(source_vault, target_vault, sample_config, invalid_file, valid_file, valid_content):
    """Test sync with ignore_errors enabled for different file combinations."""
    # Enable error ignoring
    sample_config.sync.ignore_errors = True
    sync_manager = SyncManager(source_vault, target_vault, sample_config)
    
    # Create invalid JSON to trigger error
    invalid_json = source_vault / ".obsidian" / invalid_file
    invalid_json.write_text("{invalid json}")
    
    # Create a valid file to ensure partial success
    valid_json = source_vault / ".obsidian" / valid_file
    valid_json.write_text(json.dumps(valid_content))
    
    # Sync should complete despite error
    assert sync_manager.sync_settings([invalid_file, valid_file]) is True
    
    # Verify valid file was synced
    target_valid = target_vault / ".obsidian" / valid_file
    assert target_valid.exists()
    assert json.loads(target_valid.read_text()) == valid_content 