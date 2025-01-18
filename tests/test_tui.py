"""Tests for Terminal User Interface functionality."""
import logging
from unittest.mock import create_autospec, PropertyMock, Mock
from types import SimpleNamespace
from pathlib import Path
import pytest

from obsyncit.obsync_tui import ObsidianSyncTUI, MockProgress
from obsyncit.sync import SyncManager, SyncResult
from obsyncit.schemas import Config, SyncConfig, BackupConfig
from tests.test_utils import create_test_vault

# Setup test logger
logger = logging.getLogger(__name__)


@pytest.fixture
def mock_console(monkeypatch):
    """Mock console for testing."""
    mock = Mock()
    monkeypatch.setattr("rich.console.Console.print", mock)
    return mock


@pytest.fixture
def sample_vaults(tmp_path):
    """Create sample vaults for testing."""
    vault1 = create_test_vault(tmp_path / "vault1")
    vault2 = create_test_vault(tmp_path / "vault2")
    return [vault1, vault2]


@pytest.fixture
def mock_config():
    """Create a fully mocked config with all required attributes."""
    mock_backup_config = create_autospec(BackupConfig, instance=True)
    mock_backup_config.backup_dir = Path(".backups")
    mock_backup_config.max_backups = 5

    # Create a complete mock of SyncConfig with all required attributes
    mock_sync_config = create_autospec(SyncConfig, instance=True)
    mock_dry_run = PropertyMock()
    
    # Set up all required properties
    type(mock_sync_config).dry_run = mock_dry_run
    type(mock_sync_config).ignore_errors = PropertyMock(return_value=True)
    type(mock_sync_config).core_settings = PropertyMock(return_value=True)
    type(mock_sync_config).core_plugins = PropertyMock(return_value=True)
    type(mock_sync_config).community_plugins = PropertyMock(return_value=True)
    type(mock_sync_config).themes = PropertyMock(return_value=True)
    type(mock_sync_config).snippets = PropertyMock(return_value=True)

    mock_config = create_autospec(Config, instance=True)
    mock_sync = PropertyMock(return_value=mock_sync_config)
    mock_backup = PropertyMock(return_value=mock_backup_config)
    type(mock_config).sync = mock_sync
    type(mock_config).backup = mock_backup

    return {
        "config": mock_config,
        "sync": mock_sync_config,
        "dry_run": mock_dry_run,
        "backup": mock_backup_config,
    }


def test_sync_success(mock_console, sample_vaults, mock_config, monkeypatch, caplog):
    """Test successful sync operation."""
    caplog.set_level(logging.DEBUG)
    logger.debug("Starting test_sync_success")

    # Create an autospecced SyncManager that actually calls _get_sync_items
    mock_sync_instance = create_autospec(SyncManager, instance=True)
    
    # Default successful sync result
    mock_sync_instance.sync_settings.return_value = SyncResult(
        success=True,
        items_synced=["appearance.json", "themes", "snippets"],
        items_failed=[],
        errors={},
    )
    
    # Configure the sync manager to return our sync items
    def mock_sync_settings(items=None):
        return SyncResult(
            success=True,
            items_synced=items or ["appearance.json", "themes", "snippets"],
            items_failed=[],
            errors={},
        )
    
    mock_sync_instance.sync_settings.side_effect = mock_sync_settings
    monkeypatch.setattr("obsyncit.obsync_tui.SyncManager", lambda *args, **kwargs: mock_sync_instance)

    # Set up mock prompt for vault selection
    mock_prompt = Mock(side_effect=["1", "2"])  # Source and target vault selection

    # Set up mock confirm for sync dialog
    # First pair: Skip dry run and proceed with actual sync
    mock_confirm = Mock(side_effect=[
        False,  # "Would you like to perform a dry run?" -> No
        True    # "Ready to proceed with sync?" -> Yes
    ])

    monkeypatch.setattr("rich.prompt.Prompt.ask", mock_prompt)
    monkeypatch.setattr("rich.prompt.Confirm.ask", mock_confirm)

    # Mock vault discovery
    mock_vault_discovery = Mock()
    mock_vault_discovery.find_vaults.return_value = sample_vaults

    # Create TUI instance with mocked components
    tui = ObsidianSyncTUI(progress_factory=MockProgress)
    tui.config = mock_config["config"]
    tui.vault_discovery = mock_vault_discovery

    # Run the TUI
    logger.debug("Running TUI")
    result = tui.run()

    # Verify the results
    logger.debug("Verifying test results")
    assert result is True, f"Expected successful sync but got result={result}"
    assert mock_sync_instance.sync_settings.call_count == 1, "sync_settings should be called exactly once"
    mock_config["dry_run"].assert_called_once_with(False)


def test_sync_failure(mock_console, sample_vaults, mock_config, monkeypatch, caplog):
    """Test failed sync operation."""
    caplog.set_level(logging.DEBUG)
    logger.debug("Starting test_sync_failure")

    # Create an autospecced SyncManager for failed sync
    mock_sync_instance = create_autospec(SyncManager, instance=True)
    
    # Configure the sync manager to return failed sync results
    def mock_sync_settings(items=None):
        items = items or ["appearance.json", "themes", "snippets"]
        return SyncResult(
            success=False,
            items_synced=[],
            items_failed=items,
            errors={item: f"Failed to sync {item}" for item in items}
        )
    
    mock_sync_instance.sync_settings.side_effect = mock_sync_settings
    monkeypatch.setattr("obsyncit.obsync_tui.SyncManager", lambda *args, **kwargs: mock_sync_instance)

    # Set up mock prompt for vault selection
    mock_prompt = Mock(side_effect=["1", "2"])  # Source and target vault selection

    # Set up mock confirm for sync dialog
    # Only one pair of responses as sync will fail on first try
    mock_confirm = Mock(side_effect=[
        False,  # "Would you like to perform a dry run?" -> No
        True    # "Ready to proceed with sync?" -> Yes
    ])

    monkeypatch.setattr("rich.prompt.Prompt.ask", mock_prompt)
    monkeypatch.setattr("rich.prompt.Confirm.ask", mock_confirm)

    # Mock vault discovery
    mock_vault_discovery = Mock()
    mock_vault_discovery.find_vaults.return_value = sample_vaults

    # Create TUI instance with mocked components
    tui = ObsidianSyncTUI(progress_factory=MockProgress)
    tui.config = mock_config["config"]
    tui.vault_discovery = mock_vault_discovery

    # Run the TUI
    logger.debug("Running TUI")
    result = tui.run()

    # Verify the results
    logger.debug("Verifying test results")
    assert result is False, f"Expected failed sync but got result={result}"
    assert mock_sync_instance.sync_settings.call_count == 1, "sync_settings should be called exactly once"
    mock_config["dry_run"].assert_called_once_with(False)
