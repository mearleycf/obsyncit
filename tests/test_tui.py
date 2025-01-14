"""Tests for Terminal User Interface functionality."""

from pathlib import Path
import pytest
from unittest.mock import call, Mock
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress
from obsyncit.obsync_tui import ObsidianSyncTUI
from obsyncit.errors import ObsyncError
from obsyncit.schemas import Config, SyncConfig


@pytest.fixture
def mock_console(mocker):
    """Create a mock console for testing."""
    console = mocker.Mock(spec=Console)
    console.print = mocker.Mock()
    # Mock Rich's special print methods
    console.rule = mocker.Mock()
    console.status = mocker.Mock()
    return console


@pytest.fixture
def mock_progress(mocker):
    """Create a mock progress bar."""
    progress = mocker.Mock(spec=Progress)
    progress.__enter__ = mocker.Mock(return_value=progress)
    progress.__exit__ = mocker.Mock()
    progress.add_task = mocker.Mock(return_value=1)
    return progress


@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    return Config(
        sync=SyncConfig(
            core_settings=True,
            core_plugins=True,
            community_plugins=True,
            themes=True,
            snippets=True
        )
    )


@pytest.fixture
def tui(mock_console):
    """Create a TUI instance for testing."""
    tui = ObsidianSyncTUI()
    tui.console = mock_console
    return tui


def test_display_header(tui, mock_console):
    """Test header display formatting."""
    tui.display_header()
    mock_console.print.assert_called_once()
    panel = mock_console.print.call_args[0][0]
    assert isinstance(panel, Panel)
    assert "[bold blue]Obsidian Settings Sync[/bold blue]" in str(panel.renderable)
    assert "[dim]Sync settings between Obsidian vaults[/dim]" in str(panel.renderable)


def test_get_vault_paths(tui, mocker):
    """Test vault path input handling."""
    # Mock Rich's Prompt.ask directly
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["/source/vault", "/target/vault"]

    source, target = tui.get_vault_paths()

    # Verify paths and prompts
    assert source == "/source/vault"
    assert target == "/target/vault"
    assert mock_prompt.call_count == 2
    assert mock_prompt.call_args_list[0][0][0] == "[green]Enter source vault path[/green]"
    assert mock_prompt.call_args_list[1][0][0] == "[yellow]Enter target vault path[/yellow]"


def test_display_sync_preview(tui, mock_console, tmp_path, mocker):
    """Test sync preview display."""
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()  # Create source directory to test existence check

    # Mock Table to return a predictable string
    mock_table = Mock(spec=Table)
    mock_table.title = "Sync Operation Preview"
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mock_table.__str__ = Mock(return_value=f"""
┌──────────┬────────┬────────┐
│ Setting  │ Source │ Target │
├──────────┼────────┼────────┤
│ Source   │ {source} │   ✓   │
│ Target   │ {target} │   ✗   │
└──────────┴────────┴────────┘
""")
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    tui.display_sync_preview(str(source), str(target))

    mock_console.print.assert_called_once_with(mock_table)
    assert mock_table.add_column.call_count == 3
    assert mock_table.add_row.call_count == 2


def test_run_sync_success(tui, mock_console, mocker, mock_progress):
    """Test successful sync operation through TUI."""
    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["/source", "/target"]
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [False, True]  # No dry run, yes proceed

    # Mock progress bar
    mocker.patch('obsyncit.obsync_tui.Progress', return_value=mock_progress)

    # Mock sync operation
    mock_sync_instance = Mock()
    mock_sync_instance.sync_settings.return_value = True
    mock_sync = mocker.patch('obsyncit.obsync_tui.ObsidianSettingsSync', return_value=mock_sync_instance)

    # Mock Table to avoid string representation issues
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Run TUI
    tui.run()

    # Verify sync was called
    mock_sync_instance.sync_settings.assert_called_once()
    
    # Verify progress bar was used
    mock_progress.add_task.assert_called_once_with(
        description="[green]Syncing vault settings...",
        total=None
    )
    
    # Verify success message
    mock_console.print.assert_any_call("[green]✓ Sync completed successfully![/green]")


def test_run_sync_with_dry_run(tui, mock_console, mocker, mock_progress):
    """Test sync operation with dry run enabled."""
    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["/source", "/target"]
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [True, True]  # Yes dry run, yes proceed

    # Mock progress bar
    mocker.patch('obsyncit.obsync_tui.Progress', return_value=mock_progress)

    # Mock sync operation
    mock_sync_instance = Mock()
    mock_sync_instance.sync_settings.return_value = True
    mock_sync = mocker.patch('obsyncit.obsync_tui.ObsidianSettingsSync', return_value=mock_sync_instance)

    # Mock Table to avoid string representation issues
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Run TUI
    tui.run()

    # Verify sync was called with dry_run=True in config
    mock_sync.assert_called_once()
    config = mock_sync.call_args[1]['config']
    assert config.sync.dry_run is True


def test_run_sync_failure(tui, mock_console, mocker, mock_progress):
    """Test failed sync operation through TUI."""
    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["/source", "/target"]
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [False, True]  # No dry run, yes proceed

    # Mock progress bar
    mocker.patch('obsyncit.obsync_tui.Progress', return_value=mock_progress)

    # Mock sync operation to fail
    mock_sync_instance = Mock()
    mock_sync_instance.sync_settings.return_value = False
    mocker.patch('obsyncit.obsync_tui.ObsidianSettingsSync', return_value=mock_sync_instance)

    # Mock Table to avoid string representation issues
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Run TUI
    tui.run()

    # Verify error message
    mock_console.print.assert_any_call("[red]✗ Sync failed![/red]")


def test_run_sync_error(tui, mock_console, mocker, mock_progress):
    """Test sync operation with error."""
    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["/source", "/target"]
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [False, True]  # No dry run, yes proceed

    # Mock progress bar with proper context manager behavior
    mock_progress.__enter__ = Mock(return_value=mock_progress)
    mock_progress.__exit__ = Mock(return_value=None)  # Don't swallow exceptions
    mock_progress.add_task = Mock()
    mocker.patch('obsyncit.obsync_tui.Progress', return_value=mock_progress)

    # Mock sync operation to raise error
    error = ObsyncError(
        message="Test error",
        details=f"Failed to sync between /source and /target"
    )
    
    def mock_sync_settings():
        raise error

    # Create mock with sync_settings method that raises error
    mock_sync_instance = Mock()
    mock_sync_instance.sync_settings = mock_sync_settings
    mocker.patch('obsyncit.obsync_tui.ObsidianSettingsSync', return_value=mock_sync_instance)

    # Mock Table to avoid string representation issues
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Run TUI and check exit code
    with pytest.raises(SystemExit) as exc_info:
        tui.run()
    assert exc_info.value.code == 1

    # Verify error message was printed
    error_message = f"[red]Error: {error.full_message}[/red]"
    mock_console.print.assert_any_call(error_message)


def test_run_user_cancel_confirm(tui, mock_console, mocker):
    """Test user cancellation via confirmation prompt."""
    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["/source", "/target"]
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [False, False]  # No dry run, no proceed

    # Mock Table to avoid string representation issues
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Run TUI
    tui.run()

    # Verify cancellation message
    mock_console.print.assert_any_call("[yellow]Operation cancelled by user[/yellow]")


def test_run_user_cancel_keyboard(tui, mock_console, mocker):
    """Test user cancellation via keyboard interrupt."""
    # Mock Rich's Prompt to raise KeyboardInterrupt
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = KeyboardInterrupt()

    # Run TUI and check exit code
    with pytest.raises(SystemExit) as exc_info:
        tui.run()
    assert exc_info.value.code == 0

    # Verify cancellation message
    mock_console.print.assert_any_call("\n[yellow]Operation cancelled by user[/yellow]")


def test_logging_setup(mocker):
    """Test logging configuration."""
    mock_logging = mocker.patch('obsyncit.obsync_tui.logging')
    mock_handler = mocker.patch('obsyncit.obsync_tui.RichHandler')

    ObsidianSyncTUI()

    # Verify logging was configured
    mock_logging.basicConfig.assert_called_once()
    config_kwargs = mock_logging.basicConfig.call_args[1]
    assert config_kwargs['level'] == mock_logging.INFO
    assert config_kwargs['format'] == "%(message)s" 