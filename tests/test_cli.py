"""Tests for command line interface functionality."""

import sys
import io
import tempfile
from pathlib import Path
import pytest
from unittest.mock import Mock, patch
from loguru import logger
from obsyncit.main import main
from obsyncit.errors import ConfigError
from obsyncit.vault_discovery import VaultDiscovery
from obsyncit.obsync_tui import ObsidianSyncTUI
from obsyncit.schemas.config import Config, SyncConfig


@pytest.fixture(autouse=True)
def setup_logging():
    """Set up logging for tests."""
    logger.remove()  # Remove default handlers
    logger.add(
        sys.stderr,
        format="{message}",
        level="INFO",
        colorize=False
    )


@pytest.fixture
def mock_config(mocker):
    """Mock config loading."""
    config = Config()
    config.logging.level = "INFO"
    config.sync.dry_run = False
    config.backup.max_backups = 5
    mock_load = mocker.patch('obsyncit.main.load_config', return_value=config)
    return mock_load


@pytest.fixture
def mock_sync_manager(mocker, mock_config):
    """Create a mock sync manager."""
    # Create a mock instance with a real Config object
    sync_manager = Mock()
    sync_manager.sync_settings.return_value = Mock(
        success=True,
        items_synced=["test.json"],
        items_failed=[],
        errors={},
        any_success=True,
        summary="Sync successful\nItems synced: 1"
    )
    sync_manager.list_backups.return_value = []
    sync_manager.restore_backup.return_value = True
    sync_manager.config = mock_config.return_value  # Use the real config from mock_config

    mock = mocker.patch('obsyncit.main.SyncManager', return_value=sync_manager)
    return mock


@pytest.fixture
def mock_vault_discovery(mocker):
    """Mock VaultDiscovery."""
    discovery = Mock(spec=VaultDiscovery)
    discovery.find_vaults.return_value = [Path("/test/vault1"), Path("/test/vault2")]
    mock = mocker.patch('obsyncit.main.VaultDiscovery', return_value=discovery)
    return mock


@pytest.fixture
def mock_tui(mocker):
    """Mock TUI."""
    tui = Mock(spec=ObsidianSyncTUI)
    tui.run.return_value = True
    mock = mocker.patch('obsyncit.main.ObsidianSyncTUI', return_value=tui)
    return mock


def test_cli_basic_sync(mock_sync_manager):
    """Test basic sync from CLI."""
    with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as target:
        args = [source, target]
        
        with pytest.raises(SystemExit) as exc_info:
            main(args)
        
        assert exc_info.value.code == 0
        mock_sync_manager.assert_called_once()
        mock_sync_manager.return_value.sync_settings.assert_called_once()


def test_cli_search_path(mock_vault_discovery):
    """Test CLI with custom search path."""
    with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as target:
        test_args = ["--search-path", "/custom/search/path", source, target]
        
        output = io.StringIO()
        with patch('sys.stderr', output), pytest.raises(SystemExit) as exc_info:
            main(test_args)
        
        assert exc_info.value.code == 0
        mock_vault_discovery.assert_called_once()
        mock_vault_discovery.return_value.find_vaults.assert_called_once()


def test_cli_interactive_mode(mock_tui):
    """Test CLI in interactive mode."""
    with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as target:
        test_args = ["--interactive", source, target]
        
        with pytest.raises(SystemExit) as exc_info:
            main(test_args)
        
        assert exc_info.value.code == 0
        mock_tui.assert_called_once()
        mock_tui.return_value.run.assert_called_once()


def test_cli_list_backups(mock_sync_manager):
    """Test listing backups."""
    with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as target:
        # Set up mock backups
        mock_sync_manager.return_value.list_backups.return_value = [
            "backup_20240101",
            "backup_20240102"
        ]

        test_args = [source, target, "--list-backups"]
        with pytest.raises(SystemExit) as exc_info:
            main(test_args)

        assert exc_info.value.code == 0
        mock_sync_manager.return_value.list_backups.assert_called_once()


def test_cli_restore_backup(mock_sync_manager):
    """Test restoring from backup."""
    with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as target:
        backup_name = "backup_20240101"
        test_args = [source, target, "--restore", backup_name]
        
        with pytest.raises(SystemExit) as exc_info:
            main(test_args)

        assert exc_info.value.code == 0
        mock_sync_manager.return_value.restore_backup.assert_called_once_with(Path(backup_name))


def test_cli_invalid_config(mocker):
    """Test handling of invalid configuration."""
    mock_load_config = mocker.patch('obsyncit.main.load_config', side_effect=ConfigError("Invalid config"))
    
    with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as target:
        test_args = [source, target, "--config", "invalid_config.toml"]
        
        with pytest.raises(SystemExit) as exc_info:
            main(test_args)
            
        assert exc_info.value.code == 3  # ConfigError exit code


def test_cli_vault_discovery_output(mock_vault_discovery):
    """Test vault discovery output formatting."""
    with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as target:
        test_args = ["--list-vaults", source, target]
        
        output = io.StringIO()
        with patch('sys.stderr', output), pytest.raises(SystemExit) as exc_info:
            main(test_args)
            
        assert exc_info.value.code == 0
        mock_vault_discovery.assert_called_once()
        mock_vault_discovery.return_value.find_vaults.assert_called_once()
        output_text = output.getvalue()
        assert "Found 2 vaults:" in output_text
        assert "/test/vault1" in output_text
        assert "/test/vault2" in output_text


def test_cli_config_override_precedence(mock_sync_manager, mock_vault_discovery, mock_config):
    """Test that CLI arguments override config file settings."""
    with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as target:
        # Set up test arguments
        test_args = [
            source,
            target,
            "--dry-run"  # This should override config
        ]
        
        # Run the command
        with pytest.raises(SystemExit) as exc_info:
            main(test_args)
        
        assert exc_info.value.code == 0
        
        # Verify sync was attempted
        mock_sync_manager.assert_called_once()
        
        # Verify the config was overridden by CLI args
        assert mock_config.return_value.sync.dry_run is True