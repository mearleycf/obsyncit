"""Tests for Terminal User Interface functionality."""

from pathlib import Path
import sys
from unittest.mock import Mock, patch, call
import pytest
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress
from obsyncit.obsync_tui import ObsidianSyncTUI, Status, Style, VaultPaths, SyncProgress
from obsyncit.errors import ObsyncError
from obsyncit.schemas import Config
from tests.test_utils import create_test_vault
import time


@pytest.fixture
def mock_console():
    """Create a mock console."""
    console = Mock(spec=Console)
    console.print = Mock()
    console.is_terminal = True
    console.is_interactive = True
    console.is_dumb_terminal = False
    console.is_jupyter = False
    console.size = Mock(return_value=(80, 24))
    console.get_time = Mock(return_value=time.time())
    # Add context manager protocol support
    console.__enter__ = Mock(return_value=console)
    console.__exit__ = Mock(return_value=None)
    # Add required Rich Live attributes
    console.height = 24
    console.options = {}
    console.width = 80
    console.color_system = "auto"
    # Live-specific attributes
    console.soft_wrap = False
    console.file = Mock()
    console.has_alpha = False
    console.is_terminal = True
    console.push_render_hook = Mock()
    console.clear_live = Mock()
    console.set_live = Mock()
    console.show_cursor = Mock()
    console.get_time = Mock(return_value=0.0)
    # Add default print method
    def mock_print(*args, **kwargs):
        return None
    console.print = Mock(side_effect=mock_print)
    return console


@pytest.fixture
def sample_vaults(tmp_path):
    """Create test vaults for TUI testing."""
    source = create_test_vault(tmp_path / "source")
    target = create_test_vault(tmp_path / "target")
    return [source, target]


@pytest.fixture
def mock_discovery(sample_vaults):
    """Create a mock vault discovery that returns test vaults."""
    mock = Mock()
    mock.find_vaults = Mock(return_value=sample_vaults)
    return mock


@pytest.fixture
def mock_progress():
    """Create a mock progress bar."""
    progress = Mock(spec=Progress)
    progress.__enter__ = Mock(return_value=progress)
    progress.__exit__ = Mock()
    progress.add_task = Mock(return_value=1)
    progress.stop = Mock()
    return progress


@pytest.fixture
def tui(mock_console, mock_discovery, mock_progress):
    """Create a TUI instance with mocked components."""
    with patch('obsyncit.obsync_tui.Progress', return_value=mock_progress):
        tui = ObsidianSyncTUI()
        tui.console = mock_console
        tui.vault_discovery = mock_discovery
        return tui


def test_display_header(tui):
    """Test header display."""
    tui.display_header()
    assert tui.console.print.call_count == 1
    panel = tui.console.print.call_args[0][0]
    assert isinstance(panel, Panel)
    assert panel.renderable == "[bold]Obsidian Settings Sync[/bold]\nSynchronize settings between Obsidian vaults"


def test_get_vault_paths(tui, mocker):
    """Test vault path selection."""
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]

    # Mock progress context manager
    mock_progress_ctx = Mock()
    mock_progress_ctx.__enter__ = Mock(return_value=mock_progress_ctx)
    mock_progress_ctx.__exit__ = Mock(return_value=None)
    mock_progress_ctx.start = Mock()
    mock_progress_ctx.progress = Mock()
    mock_progress_ctx.progress.update = Mock()
    mocker.patch('obsyncit.obsync_tui.SyncProgress', return_value=mock_progress_ctx)

    paths = tui.get_vault_paths()

    assert isinstance(paths.source, Path)
    assert isinstance(paths.target, Path)
    assert mock_prompt.call_count == 2


def test_display_sync_preview(tui):
    """Test sync preview display."""
    paths = VaultPaths(
        source=Path("/test/source"),
        target=Path("/test/target"),
        source_exists=True,
        target_exists=False
    )

    tui.display_sync_preview(paths)

    assert tui.console.print.call_count == 1
    table = tui.console.print.call_args[0][0]
    assert isinstance(table, Table)


def test_confirm_sync_dry_run(tui, mocker):
    """Test sync confirmation flow."""
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [True, True]
    
    result = tui.confirm_sync()
    
    assert result is True
    assert mock_confirm.call_count == 2


def test_sync_success(tui, mocker, sample_vaults):
    """Test successful sync operation."""
    # First, ensure source vault has a test file
    source = sample_vaults[0]
    obsidian_dir = source / ".obsidian"
    obsidian_dir.mkdir(parents=True, exist_ok=True)
    test_json = source / ".obsidian" / "test.json"
    test_json.write_text('{"test": true}')

    tui.vault_discovery.find_vaults.return_value = sample_vaults

    # Mock user input
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [True, False]  # dry run=True, no actual sync

    # Mock progress context manager
    mock_progress_ctx = Mock()
    mock_progress_ctx.__enter__ = Mock(return_value=mock_progress_ctx)
    mock_progress_ctx.__exit__ = Mock(return_value=None)
    mock_progress_ctx.start = Mock()
    mock_progress_ctx.progress = Mock()
    mock_progress_ctx.progress.update = Mock()
    mocker.patch('obsyncit.obsync_tui.SyncProgress', return_value=mock_progress_ctx)
    
    # Mock sync manager
    mock_sync = Mock()
    result = Mock()
    result.success = True
    result.items_synced = ["test.json"]
    mock_sync.sync_settings = Mock(return_value=result)
    mocker.patch('obsyncit.obsync_tui.SyncManager', return_value=mock_sync)

    # Run and check for success message
    tui.run()

    # Verify success messages were printed
    success_printed = False
    for call_args in tui.console.print.call_args_list:
        args = call_args[0]
        if isinstance(args[0], str) and f"{Status.SUCCESS.value}" in args[0] and (
            "Dry run completed successfully" in args[0] or
            "Sync completed successfully" in args[0]
        ):
            success_printed = True
            break
    assert success_printed


def test_sync_failure(tui, mocker):
    """Test sync failure handling."""
    # Mock user input
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [True, True]

    # Mock progress context manager
    mock_progress_ctx = Mock()
    mock_progress_ctx.__enter__ = Mock(return_value=mock_progress_ctx)
    mock_progress_ctx.__exit__ = Mock(return_value=None)
    mock_progress_ctx.start = Mock()
    mock_progress_ctx.progress = Mock()
    mock_progress_ctx.progress.update = Mock()
    mocker.patch('obsyncit.obsync_tui.SyncProgress', return_value=mock_progress_ctx)
    
    # Mock sync failure
    mock_sync = Mock()
    result = Mock()
    result.success = False
    result.errors = {"test": "error"}
    mock_sync.sync_settings = Mock(return_value=result)
    mocker.patch('obsyncit.obsync_tui.SyncManager', return_value=mock_sync)

    # Run and check for failure message
    tui.run()
    
    # Verify failure messages were printed
    failure_printed = False
    for call_args in tui.console.print.call_args_list:
        args = call_args[0]
        if isinstance(args[0], str) and f"{Status.FAILURE.value}" in args[0]:
            failure_printed = True
            break
    assert failure_printed


def test_error_handling(tui, mocker):
    """Test error handling during operation."""
    error = ObsyncError("Test error", "Details")
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = error

    with pytest.raises(SystemExit):
        tui.run()
    
    # Verify error messages were printed
    error_printed = False
    for call_args in tui.console.print.call_args_list:
        args = call_args[0]
        if isinstance(args[0], str) and "Test error" in args[0]:
            error_printed = True
            break
    assert error_printed


def test_no_vaults_found(tui):
    """Test handling when no vaults found."""
    tui.vault_discovery.find_vaults.return_value = []
    
    with pytest.raises(SystemExit):
        tui.get_vault_paths()
    
    # Verify error messages were printed
    no_vaults_printed = False
    for call_args in tui.console.print.call_args_list:
        args = call_args[0]
        if isinstance(args[0], str) and "No Obsidian vaults found" in args[0]:
            no_vaults_printed = True
            break
    assert no_vaults_printed