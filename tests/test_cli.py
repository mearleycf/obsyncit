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
    mock_instance.sync_settings.return_value = True
    mock_instance.list_backups.return_value = []
    mock_instance.restore_backup.return_value = True
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


def test_cli_basic_sync(mock_sync_manager, tmp_path, monkeypatch):
    """Test basic sync operation from CLI."""
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()

    # Mock sys.argv
    test_args = [
        "obsyncit",
        "--source", str(source),
        "--target", str(target)
    ]
    with patch.object(sys, 'argv', test_args):
        main()

    # Verify sync was called
    mock_sync_manager.assert_called_once()
    mock_sync_manager.return_value.sync_settings.assert_called_once()


def test_cli_dry_run(mock_sync_manager, tmp_path, monkeypatch):
    """Test dry run mode from CLI."""
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()

    test_args = [
        "obsyncit",
        "--dry-run",
        "--source", str(source),
        "--target", str(target)
    ]
    with patch.object(sys, 'argv', test_args):
        main()

    # Verify sync was called with dry_run=True
    mock_sync_manager.assert_called_once()
    assert mock_sync_manager.call_args[0][2].sync.dry_run is True


def test_cli_search_path(mock_vault_discovery):
    """Test CLI with custom search path."""
    search_path = "/custom/search/path"
    output = io.StringIO()
    with patch('sys.stderr', output):
        main(["--search-path", search_path, "--list-vaults"])
    mock_vault_discovery.assert_called_once()
    mock_vault_discovery.return_value.find_vaults.assert_called_once()
    assert "Found 2 vaults:" in output.getvalue()


def test_cli_interactive_mode(mock_tui):
    """Test CLI in interactive mode."""
    main(["--interactive"])
    mock_tui.assert_called_once()
    mock_tui.return_value.run.assert_called_once()


def test_cli_list_backups(mock_sync_manager, tmp_path, monkeypatch):
    """Test listing backups."""
    vault = tmp_path / "vault"
    vault.mkdir()

    # Set up mock backups
    mock_sync_manager.return_value.list_backups.return_value = [
        "backup_20240101",
        "backup_20240102"
    ]

    test_args = [
        "obsyncit",
        "--list-backups", str(vault)
    ]
    with patch.object(sys, 'argv', test_args):
        main()

    # Verify backups were listed
    mock_sync_manager.return_value.list_backups.assert_called_once()


def test_cli_restore_backup(mock_sync_manager, tmp_path, monkeypatch):
    """Test restoring from backup."""
    vault = tmp_path / "vault"
    vault.mkdir()

    test_args = [
        "obsyncit",
        "--restore", str(vault),
        "--backup", "backup_20240101"
    ]
    with patch.object(sys, 'argv', test_args):
        main()

    # Verify restore was called
    mock_sync_manager.return_value.restore_backup.assert_called_once()


def test_cli_invalid_config(tmp_path, monkeypatch):
    """Test handling of invalid configuration."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("invalid = {")

    test_args = [
        "obsyncit",
        "--config", str(config_file),
        "--source", str(tmp_path / "source"),
        "--target", str(tmp_path / "target")
    ]
    with patch.object(sys, 'argv', test_args):
        assert main() == 3  # ConfigError exit code


def test_cli_vault_discovery_output(mock_vault_discovery):
    """Test vault discovery output formatting."""
    output = io.StringIO()
    with patch('sys.stderr', output):
        main(["--list-vaults"])
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
    
    custom_path = "/custom/path"
    main(["--config", str(config_file), "--search-path", custom_path, "--list-vaults"])
    
    # Verify custom path was used instead of config file path
    mock_vault_discovery.assert_called_once()
    mock_vault_discovery.return_value.find_vaults.assert_called_once() 