"""Tests for Terminal User Interface functionality."""

from pathlib import Path
import pytest
from unittest.mock import call, Mock, patch
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress
from obsyncit.obsync_tui import ObsidianSyncTUI, Status, Style
from obsyncit.errors import ObsyncError
from obsyncit.schemas import Config
from obsyncit.sync import SyncManager
import signal
from functools import wraps
import os
import errno


def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator


@pytest.fixture
def mock_console(mocker):
    """Mock Rich console with context manager support."""
    console = Mock(spec=Console)
    console.__enter__ = Mock(return_value=console)
    console.__exit__ = Mock()
    console.is_jupyter = False
    console.is_terminal = True
    console.is_interactive = True
    console.size = Mock(return_value=(80, 24))
    console.get_time = Mock(return_value=0.0)
    return console


@pytest.fixture
def mock_vault_discovery(mocker):
    """Mock vault discovery."""
    return mocker.patch('obsyncit.vault_discovery.VaultDiscovery')


@pytest.fixture
def mock_progress(mocker):
    """Mock Rich progress with context manager support."""
    progress = Mock(spec=Progress)
    progress.__enter__ = Mock(return_value=progress)
    progress.__exit__ = Mock()
    return mocker.patch('rich.progress.Progress', return_value=progress)


@pytest.fixture
def tui(mock_console, tmp_path):
    """Create TUI instance with mocked console.
    
    Args:
        mock_console: Mocked Rich console
        tmp_path: Temporary directory for testing
        
    Returns:
        Configured TUI instance
    """
    tui = ObsidianSyncTUI(search_path=tmp_path)
    tui.console = mock_console
    return tui


def test_display_header(tui, mock_console):
    """Test header display."""
    tui.display_header()
    mock_console.print.assert_called_once()
    panel = mock_console.print.call_args[0][0]
    assert isinstance(panel, Panel)
    assert "Obsidian Settings Sync" in str(panel)


def test_get_vault_paths(tui, mocker, mock_vault_discovery):
    """Test vault path input handling."""
    # Mock vault discovery to return some test vaults
    test_vaults = [Path("/source/vault"), Path("/target/vault")]
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults

    # Mock Rich's Prompt.ask for vault selection
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]  # Select first vault for source, first remaining vault for target

    paths = tui.get_vault_paths()

    # Verify paths
    assert paths.source == test_vaults[0]
    assert paths.target == test_vaults[1]

    # Verify prompts were called with correct text
    assert mock_prompt.call_count == 2
    assert "Select source vault" in mock_prompt.call_args_list[0][0][0]
    assert "Select target vault" in mock_prompt.call_args_list[1][0][0]


def test_display_sync_preview(tui, mock_console, tmp_path):
    """Test sync preview display."""
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()  # Create source directory to test existence check

    # Create test paths object
    paths = Mock()
    paths.source = source
    paths.target = target
    paths.source_exists = True
    paths.target_exists = False

    tui.display_sync_preview(paths)

    # Verify table was printed
    mock_console.print.assert_called_once()
    table = mock_console.print.call_args[0][0]
    assert isinstance(table, Table)


def test_confirm_sync_dry_run(tui, mocker):
    """Test sync confirmation with dry run."""
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [True, True]  # Yes to dry run, yes to proceed

    result = tui.confirm_sync()
    assert result is True
    assert mock_confirm.call_count == 2


def test_run_sync_success(tui, mock_console, mocker, mock_progress, mock_vault_discovery):
    """Test successful sync operation through TUI."""
    # Mock vault discovery
    test_vaults = [Path("/source"), Path("/target")]
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults

    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]  # Select first vault for source, first remaining vault for target
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [True, True]  # Yes to dry run, yes to proceed

    # Mock sync operation
    mock_sync = Mock()
    mock_sync.sync_settings.return_value.success = True
    mocker.patch('obsyncit.sync.SyncManager', return_value=mock_sync)

    # Run TUI
    tui.run()

    # Verify success message
    success_message = next(
        call[0][0] for call in mock_console.print.call_args_list
        if isinstance(call[0][0], str) and Status.SUCCESS.value in call[0][0]
    )
    assert "completed successfully" in success_message


def test_run_sync_failure(tui, mock_console, mocker, mock_progress, mock_vault_discovery):
    """Test sync failure handling."""
    # Mock vault discovery
    test_vaults = [Path("/source"), Path("/target")]
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults

    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [True, True]

    # Mock sync operation to fail
    mock_sync = Mock()
    mock_sync.sync_settings.return_value.success = False
    mock_sync.sync_settings.return_value.errors = {"test": "error"}
    mocker.patch('obsyncit.sync.SyncManager', return_value=mock_sync)

    # Run TUI
    tui.run()

    # Verify error message
    error_message = next(
        call[0][0] for call in mock_console.print.call_args_list
        if isinstance(call[0][0], str) and Status.FAILURE.value in call[0][0]
    )
    assert "failed" in error_message


def test_error_handling(tui, mock_console):
    """Test error display formatting."""
    error_msg = "Test error"
    error_details = "Error details"

    # Simulate error
    with pytest.raises(SystemExit):
        tui.console.print(f"[{Style.ERROR.value}]Error: {error_msg}[/]")
        if error_details:
            tui.console.print(f"[{Style.DIM.value}]Details: {error_details}[/]")
        raise ObsyncError(error_msg, error_details)

    # Verify error message formatting
    error_calls = [
        call[0][0] for call in mock_console.print.call_args_list 
        if isinstance(call[0][0], str) and f"[{Style.ERROR.value}]" in call[0][0]
    ]
    assert any(error_msg in call for call in error_calls)


def test_no_vaults_found(tui, mock_console, mock_vault_discovery):
    """Test handling when no vaults are found."""
    mock_vault_discovery.return_value.find_vaults.return_value = []

    with pytest.raises(SystemExit):
        tui.get_vault_paths()

    # Verify error message
    error_message = next(
        call[0][0] for call in mock_console.print.call_args_list
        if isinstance(call[0][0], str) and "No Obsidian vaults found" in call[0][0]
    )
    assert f"[{Style.ERROR.value}]" in error_message


def test_sync_progress_display(tui, mock_console, mocker, mock_progress, mock_vault_discovery):
    """Test progress display during sync."""
    # Mock vault discovery
    test_vaults = [Path("/source"), Path("/target")]
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults

    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [True, True]

    # Mock successful sync
    mock_sync = Mock()
    mock_sync.sync_settings.return_value.success = True
    mocker.patch('obsyncit.sync.SyncManager', return_value=mock_sync)

    # Run TUI
    tui.run()

    # Verify progress was shown
    assert mock_progress.return_value.__enter__.called
    assert mock_progress.return_value.__exit__.called