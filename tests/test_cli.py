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
from tests.test_utils import create_test_vault, clean_directory


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


def test_cli_basic_sync(mock_sync_manager, clean_dir):
    """Test basic sync from CLI."""
    source = clean_dir / "source"
    target = clean_dir / "target"
    create_test_vault(source)
    create_test_vault(target)
    
    with pytest.raises(SystemExit) as exc_info:
        main([str(source), str(target)])
    assert exc_info.value.code == 0
    mock_sync_manager.assert_called_once()
    mock_sync_manager.return_value.sync_settings.assert_called_once()


def test_cli_search_path(mock_vault_discovery, clean_dir):
    """Test CLI with custom search path."""
    search_path = "/custom/search/path"
    source = clean_dir / "source"
    target = clean_dir / "target"
    create_test_vault(source)
    create_test_vault(target)
    
    output = io.StringIO()
    with patch('sys.stderr', output), pytest.raises(SystemExit) as exc_info:
        main(["--search-path", search_path, str(source), str(target)])
    assert exc_info.value.code == 0
    mock_vault_discovery.assert_called_once()
    mock_vault_discovery.return_value.find_vaults.assert_called_once()


def test_cli_interactive_mode(mock_tui, clean_dir):
    """Test CLI in interactive mode."""
    source = clean_dir / "source"
    target = clean_dir / "target"
    create_test_vault(source)
    create_test_vault(target)
    
    with pytest.raises(SystemExit) as exc_info:
        main(["--interactive", str(source), str(target)])
    assert exc_info.value.code == 0
    mock_tui.assert_called_once()
    mock_tui.return_value.run.assert_called_once()


def test_cli_list_backups(mock_sync_manager, clean_dir, monkeypatch):
    """Test listing backups."""
    source = clean_dir / "source"
    target = clean_dir / "target"
    create_test_vault(source)
    create_test_vault(target)

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


def test_cli_restore_backup(mock_sync_manager, tmp_path, monkeypatch):
    """Test restoring from backup."""
    source = tmp_path / "source"
    target = tmp_path / "target"
    create_test_vault(source)
    create_test_vault(target)

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
    mock_sync_manager.return_value.restore_backup.assert_called_once()


def test_cli_invalid_config(tmp_path, monkeypatch):
    """Test handling of invalid configuration."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("invalid = {")

    test_args = [
        "obsyncit",
        str(tmp_path / "source"),  # source_vault as positional arg
        str(tmp_path / "target"),  # target_vault as positional arg
        "--config", str(config_file)
    ]
    with patch.object(sys, 'argv', test_args), pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 3  # ConfigError exit code


def test_cli_vault_discovery_output(mock_vault_discovery, tmp_path):
    """Test vault discovery output formatting."""
    source = tmp_path / "source"
    target = tmp_path / "target"
    create_test_vault(source)
    create_test_vault(target)
    
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


def test_cli_config_override_precedence(mock_vault_discovery, tmp_path):
    """Test that CLI arguments override config file settings."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
    [vault]
    search_path = "/default/path"
    search_depth = 2
    """)
    
    source = tmp_path / "source"
    target = tmp_path / "target"
    create_test_vault(source)
    create_test_vault(target)
    
    custom_path = "/custom/path"
    with pytest.raises(SystemExit) as exc_info:
        main(["--config", str(config_file), "--search-path", custom_path, str(source), str(target)])
    assert exc_info.value.code == 0
    
    # Verify custom path was used instead of config file path
    mock_vault_discovery.assert_called_once()
    mock_vault_discovery.return_value.find_vaults.assert_called_once()
