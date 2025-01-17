"""Tests for command line interface functionality."""

import sys
import io
from pathlib import Path
import pytest
from unittest.mock import Mock, patch
from loguru import logger
from obsyncit.main import main
from obsyncit.errors import ConfigError
from obsyncit.vault_discovery import VaultDiscovery
from obsyncit.obsync_tui import ObsidianSyncTUI
from tests.test_utils import create_test_vault


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
    config = Mock()
    config.vault = Mock(search_path="/default/path", search_depth=2)
    config.sync = Mock(dry_run=False, backup_before_sync=True, max_backups=5)
    config.logging = Mock(level="INFO")
    mock_load = mocker.patch('obsyncit.main.load_config', return_value=config)
    return mock_load

@pytest.fixture
def mock_sync_manager(mocker):
    """Create a mock sync manager."""
    mock = mocker.patch('obsyncit.main.SyncManager')
    mock_instance = Mock()
    mock_instance.sync_settings.return_value = Mock(
        success=True,
        items_synced=["test.json"],
        items_failed=[],
        errors={},
        any_success=True,
        summary="Sync successful\nItems synced: 1"
    )
    mock_instance.list_backups.return_value = []
    mock_instance.restore_backup.return_value = True
    
    # Mock config object with property to track dry_run changes
    config = Mock()
    config.sync = Mock()
    config.sync.dry_run = False
    mock_instance.config = config
    
    mock.return_value = mock_instance
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


@patch('pathlib.Path.exists')
@patch('pathlib.Path.is_dir')
def test_cli_basic_sync(mock_is_dir, mock_exists, mock_sync_manager):
    """Test basic sync from CLI."""
    # Mock filesystem checks
    mock_exists.return_value = True
    mock_is_dir.return_value = True
    
    source = Path("/mock/source")
    target = Path("/mock/target")
    
    with pytest.raises(SystemExit) as exc_info:
        main([str(source), str(target)])
    assert exc_info.value.code == 0
    mock_sync_manager.assert_called_once()
    mock_sync_manager.return_value.sync_settings.assert_called_once()


@patch('pathlib.Path.exists')
@patch('pathlib.Path.is_dir')
def test_cli_search_path(mock_is_dir, mock_exists, mock_vault_discovery):
    """Test CLI with custom search path."""
    # Mock filesystem checks
    mock_exists.return_value = True
    mock_is_dir.return_value = True
    
    search_path = "/custom/search/path"
    source = Path("/mock/source")
    target = Path("/mock/target")
    
    output = io.StringIO()
    with patch('sys.stderr', output), pytest.raises(SystemExit) as exc_info:
        main(["--search-path", search_path, str(source), str(target)])
    assert exc_info.value.code == 0
    mock_vault_discovery.assert_called_once()
    mock_vault_discovery.return_value.find_vaults.assert_called_once()


@patch('pathlib.Path.exists')
@patch('pathlib.Path.is_dir')
def test_cli_interactive_mode(mock_is_dir, mock_exists, mock_tui):
    """Test CLI in interactive mode."""
    # Mock filesystem checks
    mock_exists.return_value = True
    mock_is_dir.return_value = True
    
    source = Path("/mock/source")
    target = Path("/mock/target")
    
    with pytest.raises(SystemExit) as exc_info:
        main(["--interactive", str(source), str(target)])
    assert exc_info.value.code == 0
    mock_tui.assert_called_once()
    mock_tui.return_value.run.assert_called_once()


@patch('pathlib.Path.exists')
@patch('pathlib.Path.is_dir')
def test_cli_list_backups(mock_is_dir, mock_exists, mock_sync_manager):
    """Test listing backups."""
    # Mock filesystem checks
    mock_exists.return_value = True
    mock_is_dir.return_value = True
    
    source = Path("/mock/source")
    target = Path("/mock/target")

    # Set up mock backups
    mock_sync_manager.return_value.list_backups.return_value = [
        "backup_20240101",
        "backup_20240102"
    ]

    test_args = [
        "obsyncit",
        str(source),  # source_vault as positional arg
        str(target),  # target_vault as positional arg
        "--list-backups"
    ]
    with patch.object(sys, 'argv', test_args), pytest.raises(SystemExit) as exc_info:
        main()

    # Verify backups were listed and exit code is 0
    assert exc_info.value.code == 0
    mock_sync_manager.return_value.list_backups.assert_called_once()


@patch('pathlib.Path.exists')
@patch('pathlib.Path.is_dir')
def test_cli_restore_backup(mock_is_dir, mock_exists, mock_sync_manager):
    """Test restoring from backup."""
    # Mock filesystem checks
    mock_exists.return_value = True
    mock_is_dir.return_value = True
    
    source = Path("/mock/source")
    target = Path("/mock/target")

    test_args = [
        "obsyncit",
        str(source),  # source_vault as positional arg
        str(target),  # target_vault as positional arg
        "--restore", "backup_20240101"
    ]
    with patch.object(sys, 'argv', test_args), pytest.raises(SystemExit) as exc_info:
        main()

    # Verify restore was called and exit code is 0
    assert exc_info.value.code == 0
    mock_sync_manager.return_value.restore_backup.assert_called_once_with(Path("backup_20240101"))


@patch('pathlib.Path.exists')
@patch('pathlib.Path.is_dir')
@patch('pathlib.Path.read_text')
def test_cli_invalid_config(mock_read_text, mock_is_dir, mock_exists):
    """Test handling of invalid configuration."""
    # Mock filesystem checks
    mock_exists.return_value = True
    mock_is_dir.return_value = True
    mock_read_text.return_value = "invalid = {"
    
    config_file = Path("/mock/config.toml")
    source = Path("/mock/source")
    target = Path("/mock/target")

    test_args = [
        "obsyncit",
        str(source),  # source_vault as positional arg
        str(target),  # target_vault as positional arg
        "--config", str(config_file)
    ]
    with patch.object(sys, 'argv', test_args), pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 3  # ConfigError exit code


@patch('pathlib.Path.exists')
@patch('pathlib.Path.is_dir')
def test_cli_vault_discovery_output(mock_is_dir, mock_exists, mock_vault_discovery):
    """Test vault discovery output formatting."""
    # Mock filesystem checks
    mock_exists.return_value = True
    mock_is_dir.return_value = True
    
    source = Path("/mock/source")
    target = Path("/mock/target")
    
    # Mock vault discovery to return test paths
    mock_vault_discovery.return_value.find_vaults.return_value = [
        Path("/test/vault1"),
        Path("/test/vault2")
    ]
    
    output = io.StringIO()
    with patch('sys.stderr', output), pytest.raises(SystemExit) as exc_info:
        main(["--list-vaults", str(source), str(target)])
    assert exc_info.value.code == 0
    mock_vault_discovery.assert_called_once()
    mock_vault_discovery.return_value.find_vaults.assert_called_once()
    output_text = output.getvalue()
    assert "Found 2 vaults:" in output_text
    assert "/test/vault1" in output_text
    assert "/test/vault2" in output_text


@patch('pathlib.Path.exists')
@patch('pathlib.Path.is_dir')
def test_cli_config_override_precedence(
    mock_is_dir,
    mock_exists,
    mock_sync_manager,
    mock_vault_discovery,
    mock_config
):
    """Test that CLI arguments override config file settings."""
    # Mock filesystem checks
    mock_exists.return_value = True
    mock_is_dir.return_value = True
    
    source = Path("/mock/source")
    target = Path("/mock/target")
    custom_path = "/custom/path"
    
    # Test with CLI arguments that should override config
    test_args = [
        str(source),
        str(target),
        "--search-path", custom_path,
        "--dry-run"  # Add this to test sync config override
    ]
    
    with pytest.raises(SystemExit) as exc_info:
        main(test_args)
    
    assert exc_info.value.code == 0
    
    # Verify custom search path was used
    mock_vault_discovery.assert_called_once()
    mock_vault_discovery.return_value.find_vaults.assert_called_once()
    
    # Verify sync manager was created with overridden config
    mock_sync_manager.assert_called_once()
    
    # Verify dry-run override was applied
    assert mock_sync_manager.return_value.config.sync.dry_run is True
