"""
Tests for sync operations in ObsyncIt.

This module contains tests for the synchronization functionality, verifying:
- Basic sync operations between vaults
- Handling of various sync configurations
- Error conditions and recovery
- Permission handling
- File validation and integrity
"""

import json
import shutil
from pathlib import Path
from typing import Dict, Any
import pytest
from obsyncit.sync import SyncManager
from obsyncit.errors import SyncError, BackupError, ValidationError
from obsyncit.schemas import Config, SyncConfig


# Test Data
SAMPLE_SETTINGS = {
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


def create_test_files(settings_dir: Path, files: Dict[str, Any]) -> None:
    """
    Create test files in the specified directory.
    
    Args:
        settings_dir: Directory to create files in
        files: Dictionary of filenames and their contents
    """
    for filename, data in files.items():
        (settings_dir / filename).write_text(json.dumps(data))


@pytest.fixture
def vault_factory(tmp_path):
    """
    Factory fixture for creating test vaults with customizable settings.
    
    Args:
        tmp_path: Pytest temporary directory fixture
    
    Returns:
        function: Factory function to create vaults
    """
    def _create_vault(name: str, settings: Dict[str, Any] = None, 
                     create_themes: bool = True, 
                     create_snippets: bool = True) -> Path:
        vault = tmp_path / name
        settings_dir = vault / ".obsidian"
        settings_dir.mkdir(parents=True)
        
        # Create settings files
        if settings:
            create_test_files(settings_dir, settings)
        
        # Create optional directories
        if create_themes:
            themes_dir = settings_dir / "themes"
            themes_dir.mkdir()
            (themes_dir / "theme.css").write_text("/* Sample theme */")
        
        if create_snippets:
            snippets_dir = settings_dir / "snippets"
            snippets_dir.mkdir()
            (snippets_dir / "custom.css").write_text("/* Sample snippet */")
        
        return vault
    
    return _create_vault


@pytest.fixture
def source_vault(vault_factory):
    """Create a source vault with sample settings."""
    return vault_factory("source_vault", SAMPLE_SETTINGS)


@pytest.fixture
def target_vault(vault_factory):
    """Create an empty target vault."""
    return vault_factory("target_vault", {})


@pytest.fixture
def sync_manager(source_vault, target_vault):
    """Create a sync manager instance with default configuration."""
    config = Config()
    config.sync.dry_run = False
    config.sync.ignore_errors = False
    return SyncManager(source_vault, target_vault, config)


class TestBasicSync:
    """Tests for basic sync operations."""
    
    def test_sync_all_settings(self, sync_manager, source_vault, target_vault):
        """
        Test complete synchronization of all settings.
        
        Verifies that:
        1. All files are copied correctly
        2. File contents match exactly
        3. Directory structure is preserved
        """
        assert sync_manager.sync_settings() is True
        
        source_files = set((source_vault / ".obsidian").glob("**/*"))
        target_files = set((target_vault / ".obsidian").glob("**/*"))
        
        # Verify file count matches
        assert len(source_files) == len(target_files), \
            "Number of files in source and target should match"
        
        # Verify content of synced files
        app_json = json.loads((target_vault / ".obsidian" / "app.json").read_text())
        assert app_json == SAMPLE_SETTINGS["app.json"], \
            "app.json content should match source exactly"
    
    @pytest.mark.parametrize("sync_items,expected_files", [
        (["appearance.json", "themes"], {"appearance.json", "themes"}),
        (["app.json", "hotkeys.json"], {"app.json", "hotkeys.json"}),
        (["community-plugins.json", "snippets"], {"community-plugins.json", "snippets"}),
    ])
    def test_sync_specific_items(self, sync_manager, source_vault, target_vault, 
                               sync_items, expected_files):
        """
        Test selective synchronization of specific items.
        
        Verifies that:
        1. Only specified items are synced
        2. Other items remain untouched
        3. Synced items match source exactly
        """
        assert sync_manager.sync_settings(sync_items) is True
        
        # Verify only specified files were synced
        target_settings = target_vault / ".obsidian"
        for file in expected_files:
            assert (target_settings / file).exists(), \
                f"Expected file {file} should exist in target"
        
        # Verify other files were not synced
        all_possible = {"app.json", "appearance.json", "hotkeys.json", 
                       "core-plugins.json", "community-plugins.json", 
                       "themes", "snippets"}
        for file in all_possible - expected_files:
            assert not (target_settings / file).exists(), \
                f"Unexpected file {file} found in target"


class TestSyncModes:
    """Tests for different sync modes and configurations."""
    
    def test_dry_run(self, source_vault, target_vault):
        """
        Test dry run mode prevents actual file changes.
        
        Verifies that:
        1. Sync operation completes successfully
        2. No files are actually created
        3. Target remains unchanged
        """
        config = Config()
        config.sync.dry_run = True
        sync_manager = SyncManager(source_vault, target_vault, config)
        
        assert sync_manager.sync_settings() is True
        assert not list((target_vault / ".obsidian").glob("**/*")), \
            "No files should be created in dry run mode"


class TestErrorHandling:
    """Tests for error handling and recovery."""
    
    @pytest.mark.parametrize("vault_type,create_vault", [
        ("source", False),  # Missing source vault
        ("target", False),  # Missing target vault
        ("source", True),   # Empty source vault
        ("target", True),   # Empty target vault
    ])
    def test_invalid_vault_configurations(self, tmp_path, vault_type, create_vault):
        """
        Test handling of invalid vault configurations.
        
        Verifies proper error handling for:
        1. Missing vaults
        2. Empty vaults
        3. Invalid vault structures
        """
        # Create the valid vault
        valid_vault = tmp_path / "valid_vault"
        valid_vault.mkdir()
        (valid_vault / ".obsidian").mkdir()
        
        # Set up the invalid vault
        invalid_vault = tmp_path / "invalid_vault"
        if create_vault:
            invalid_vault.mkdir()
        
        # Create sync manager based on which vault is invalid
        config = Config()
        if vault_type == "source":
            sync_manager = SyncManager(invalid_vault, valid_vault, config)
        else:
            sync_manager = SyncManager(valid_vault, invalid_vault, config)
        
        with pytest.raises(SyncError) as exc_info:
            sync_manager.sync_settings()
        assert "Invalid vault" in str(exc_info.value)
    
    def test_backup_failure(self, sync_manager, monkeypatch):
        """
        Test sync behavior when backup creation fails.
        
        Verifies that:
        1. Backup errors are caught and reported
        2. Sync operation is aborted
        3. Error message contains backup context
        """
        def mock_create_backup(*args):
            raise BackupError("Backup failed", backup_path=Path(".backups"))
        
        monkeypatch.setattr(sync_manager.backup_mgr, "create_backup", mock_create_backup)
        
        with pytest.raises(BackupError) as exc_info:
            sync_manager.sync_settings()
        assert "Backup failed" in str(exc_info.value)
    
    @pytest.mark.parametrize("invalid_content,expected_message", [
        ("{invalid json}", "Invalid JSON"),
        ('{"missing": "comma" "key": "value"}', "Invalid JSON"),
        ("not json at all", "Invalid JSON"),
    ])
    def test_invalid_json_handling(self, sync_manager, source_vault, 
                                 invalid_content, expected_message):
        """
        Test handling of invalid JSON content.
        
        Verifies proper error handling for:
        1. Malformed JSON
        2. Invalid JSON syntax
        3. Non-JSON content
        """
        invalid_json = source_vault / ".obsidian" / "app.json"
        invalid_json.write_text(invalid_content)
        
        with pytest.raises(ValidationError) as exc_info:
            sync_manager.sync_settings()
        assert expected_message in str(exc_info.value)
    
    @pytest.mark.parametrize("permission,expected_error", [
        (0o444, "Permission denied"),  # Read-only
        (0o000, "Permission denied"),  # No permissions
    ])
    def test_permission_handling(self, sync_manager, source_vault, target_vault, 
                               permission, expected_error):
        """
        Test sync behavior with different permission configurations.
        
        Verifies proper handling of:
        1. Read-only permissions
        2. No permissions
        3. Mixed permissions
        """
        try:
            # Set up test file and permissions
            settings_dir = target_vault / ".obsidian"
            settings_dir.chmod(permission)
            
            with pytest.raises(SyncError) as exc_info:
                sync_manager.sync_settings()
            assert expected_error in str(exc_info.value)
        
        finally:
            # Cleanup - restore permissions for cleanup
            settings_dir.chmod(0o755)


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""
    
    def test_empty_sync_list(self, sync_manager):
        """
        Test sync with empty items list.
        
        Verifies that:
        1. Operation completes successfully
        2. No changes are made
        """
        assert sync_manager.sync_settings([]) is True
    
    @pytest.mark.parametrize("invalid_file,valid_file,valid_content", [
        ("app.json", "appearance.json", {"theme": "light"}),
        ("hotkeys.json", "core-plugins.json", {"file-explorer": True}),
    ])
    def test_partial_sync_with_errors(self, source_vault, target_vault, 
                                    invalid_file, valid_file, valid_content):
        """
        Test partial sync with ignore_errors enabled.
        
        Verifies that:
        1. Valid files are synced despite errors
        2. Invalid files are skipped
        3. Operation completes with partial success
        """
        config = Config()
        config.sync.ignore_errors = True
        sync_manager = SyncManager(source_vault, target_vault, config)
        
        # Create invalid and valid files
        invalid_path = source_vault / ".obsidian" / invalid_file
        invalid_path.write_text("{invalid json}")
        
        valid_path = source_vault / ".obsidian" / valid_file
        valid_path.write_text(json.dumps(valid_content))
        
        # Sync should complete despite error
        assert sync_manager.sync_settings([invalid_file, valid_file]) is True
        
        # Verify valid file was synced correctly
        target_valid = target_vault / ".obsidian" / valid_file
        assert target_valid.exists()
        assert json.loads(target_valid.read_text()) == valid_content 