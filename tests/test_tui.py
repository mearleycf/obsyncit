"""Tests for Terminal User Interface functionality."""

from pathlib import Path
import pytest
from unittest.mock import call, Mock, patch
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress
from obsyncit.obsync_tui import ObsidianSyncTUI
from obsyncit.errors import ObsyncError
from obsyncit.schemas import Config, SyncConfig
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
def mock_progress(mocker):
    """Create a mock progress bar."""
    # Create the mock with proper context manager behavior
    progress = mocker.Mock(spec=Progress)
    progress.__enter__ = mocker.Mock(return_value=progress)
    progress.__exit__ = mocker.Mock(return_value=None)
    progress.add_task = mocker.Mock(return_value=1)
    progress.update = mocker.Mock()
    
    # Create a mock Progress class that returns our mock instance
    mock_progress_class = mocker.Mock(return_value=progress)
    mocker.patch('obsyncit.obsync_tui.Progress', new=mock_progress_class)
    
    return progress


@pytest.fixture
def mock_vault_discovery(mocker):
    """Create a mock vault discovery."""
    mock = mocker.patch('obsyncit.obsync_tui.VaultDiscovery')
    mock_instance = Mock()
    test_vaults = [Path("/source"), Path("/target")]
    mock_instance.find_vaults.return_value = test_vaults
    
    def get_vault_info(vault):
        return {
            "name": vault.name,
            "path": str(vault),
            "settings_count": 5,
            "plugin_count": 3
        }
    mock_instance.get_vault_info.side_effect = get_vault_info
    mock.return_value = mock_instance
    return mock


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
def tui(mock_console, mock_vault_discovery):
    """Create TUI instance for testing."""
    tui = ObsidianSyncTUI(console=mock_console)
    tui.vault_discovery = mock_vault_discovery.return_value
    return tui


@pytest.fixture
def mock_sync(mocker):
    """Mock SyncManager."""
    sync = Mock(spec=SyncManager)
    sync.sync_settings = Mock(return_value=True)
    mocker.patch('obsyncit.obsync_tui.SyncManager', return_value=sync)
    return sync


def test_display_header(tui, mock_console):
    """Test header display formatting."""
    tui.display_header()
    mock_console.print.assert_called_once()
    panel = mock_console.print.call_args[0][0]
    assert isinstance(panel, Panel)
    assert "[bold blue]Obsidian Settings Sync[/bold blue]" in str(panel.renderable)
    assert "[dim]Sync settings between Obsidian vaults[/dim]" in str(panel.renderable)


def test_get_vault_paths(tui, mocker, mock_vault_discovery):
    """Test vault path input handling."""
    # Mock vault discovery to return some test vaults
    test_vaults = [Path("/source/vault"), Path("/target/vault")]
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults
    mock_vault_discovery.return_value.get_vault_info.return_value = {
        "settings_count": 5,
        "plugin_count": 3
    }

    # Mock Rich's Prompt.ask for vault selection
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]  # Select first vault for source, first remaining vault for target

    config = Config()
    source, target = tui.get_vault_paths(config)

    # Verify paths
    assert source == str(test_vaults[0])
    assert target == str(test_vaults[1])

    # Verify prompts were called with correct text
    assert mock_prompt.call_count == 2
    assert "Select source vault" in mock_prompt.call_args_list[0][0][0]
    assert "Select target vault" in mock_prompt.call_args_list[1][0][0]


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


def test_run_sync_success(tui, mock_console, mocker, mock_progress, mock_vault_discovery):
    """Test successful sync operation through TUI."""
    # Mock vault discovery
    test_vaults = [Path("/source"), Path("/target")]
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults
    mock_vault_discovery.return_value.get_vault_info.return_value = {
        "settings_count": 5,
        "plugin_count": 3
    }

    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]  # Select first vault for source, first remaining vault for target
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [False, True]  # No dry run, yes proceed

    # Mock progress bar with proper context manager behavior
    mock_progress.__enter__ = Mock(return_value=mock_progress)
    mock_progress.__exit__ = Mock(return_value=None)  # Don't swallow exceptions
    mock_progress.add_task = Mock(return_value=1)
    mock_progress.update = Mock()
    mocker.patch('obsyncit.obsync_tui.Progress', return_value=mock_progress)

    # Mock sync operation
    mock_sync_instance = Mock()
    mock_sync_instance.sync_settings = Mock(return_value=True)
    mock_sync = mocker.patch('obsyncit.obsync_tui.SyncManager')
    mock_sync.return_value = mock_sync_instance

    # Mock Table
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Run TUI
    tui.run()

    # Verify sync was called with correct arguments
    mock_sync.assert_called_once()
    call_args = mock_sync.call_args[1]
    assert call_args['source_vault'] == str(test_vaults[0])
    assert call_args['target_vault'] == str(test_vaults[1])
    assert not call_args['config'].sync.dry_run

    # Verify sync_settings was called
    mock_sync_instance.sync_settings.assert_called_once()
    
    # Verify progress bar was used for both vault discovery and sync
    assert mock_progress.add_task.call_count == 2
    mock_progress.add_task.assert_has_calls([
        call(description="[green]Searching for vaults...", total=None),
        call(description="[green]Syncing vault settings...", total=None)
    ])
    
    # Verify success message
    mock_console.print.assert_any_call("[green]✓ Sync completed successfully![/green]")


def test_run_sync_with_dry_run(tui, mock_console, mocker, mock_progress, mock_vault_discovery):
    """Test sync operation with dry run enabled."""
    # Mock vault discovery
    test_vaults = [Path("/source"), Path("/target")]
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults
    mock_vault_discovery.return_value.get_vault_info.return_value = {
        "settings_count": 5,
        "plugin_count": 3
    }

    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]  # Select first vault for source, first remaining vault for target
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [True, True]  # Yes dry run, yes proceed

    # Mock progress bar
    mocker.patch('obsyncit.obsync_tui.Progress', return_value=mock_progress)

    # Mock sync operation
    mock_sync_instance = Mock()
    mock_sync_instance.sync_settings.return_value = True
    mock_sync = mocker.patch('obsyncit.obsync_tui.SyncManager', return_value=mock_sync_instance)

    # Mock Table
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


def test_run_sync_failure(tui, mock_console, mocker, mock_progress, mock_vault_discovery):
    """Test failed sync operation through TUI."""
    # Mock vault discovery
    test_vaults = [Path("/source"), Path("/target")]
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults
    mock_vault_discovery.return_value.get_vault_info.return_value = {
        "settings_count": 5,
        "plugin_count": 3
    }

    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]  # Select first vault for source, first remaining vault for target
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [False, True]  # No dry run, yes proceed

    # Mock progress bar
    mocker.patch('obsyncit.obsync_tui.Progress', return_value=mock_progress)

    # Mock sync operation to fail
    mock_sync_instance = Mock()
    mock_sync_instance.sync_settings.return_value = False
    mocker.patch('obsyncit.obsync_tui.SyncManager', return_value=mock_sync_instance)

    # Mock Table
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Run TUI
    tui.run()

    # Verify error message
    mock_console.print.assert_any_call("[red]✗ Sync failed![/red]")


def test_run_sync_error(tui, mock_console, mocker, mock_progress, mock_vault_discovery):
    """Test sync operation with error."""
    # Mock logging
    mock_logging = mocker.patch('obsyncit.obsync_tui.logging')
    
    # Mock vault discovery
    test_vaults = [Path("/source"), Path("/target")]
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults
    
    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]  # Select first vault for source, first remaining vault for target
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [False, True]  # No dry run, yes proceed

    # Mock sync operation to raise error
    error = ObsyncError(
        message="Test error",
        details="Failed to sync between /source and /target"
    )
    
    mock_sync_instance = Mock()
    mock_sync_instance.sync_settings = Mock(side_effect=error)
    mocker.patch('obsyncit.obsync_tui.SyncManager', return_value=mock_sync_instance)

    # Mock Table
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Run TUI and check exit code
    with pytest.raises(SystemExit) as exc_info:
        tui.run()
    assert exc_info.value.code == 1

    # Verify error message was printed
    error_message = f"[red]Error: {str(error)}[/red]"
    mock_console.print.assert_any_call(error_message)
    
    # Verify logging
    mock_logging.exception.assert_called_once_with("Unexpected error")


def test_run_user_cancel_confirm(tui, mock_console, mocker, mock_progress, mock_vault_discovery):
    """Test user cancellation via confirmation prompt."""
    # Mock vault discovery
    test_vaults = [Path("/source"), Path("/target")]
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults
    mock_vault_discovery.return_value.get_vault_info.return_value = {
        "settings_count": 5,
        "plugin_count": 3
    }

    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]  # Select first vault for source, first remaining vault for target
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [False, False]  # No dry run, no proceed

    # Mock progress bar with proper context manager behavior
    mock_progress.__enter__ = Mock(return_value=mock_progress)
    mock_progress.__exit__ = Mock(return_value=None)
    mock_progress.add_task = Mock(return_value=1)
    mock_progress.update = Mock()
    mocker.patch('obsyncit.obsync_tui.Progress', return_value=mock_progress)

    # Mock Table
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Run TUI
    tui.run()

    # Verify cancellation message
    mock_console.print.assert_any_call("[yellow]Operation cancelled by user[/yellow]")

    # Verify progress bar was used for vault discovery
    mock_progress.add_task.assert_called_once_with(
        description="[green]Searching for vaults...",
        total=None
    )


def test_run_user_cancel_keyboard(tui, mock_console, mocker):
    """Test user cancellation via keyboard interrupt."""
    # Mock vault discovery to ensure it's properly initialized
    mock_vault_discovery = mocker.patch('obsyncit.obsync_tui.VaultDiscovery')
    mock_instance = Mock()
    mock_instance.find_vaults.side_effect = KeyboardInterrupt()
    mock_vault_discovery.return_value = mock_instance

    # Run TUI
    tui.run()

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


@pytest.mark.timeout(5)
def test_progress_bar_updates(tui, mock_console, mocker, mock_progress, mock_vault_discovery):
    """Test progress bar updates during sync operation."""
    # Mock vault discovery
    test_vaults = [Path("/source"), Path("/target")]
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults
    
    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]  # Select first vault for source, first remaining vault for target
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [False, True]  # No dry run, yes proceed

    # Mock sync operation with progress updates
    mock_sync_instance = Mock()
    def sync_with_progress():
        mock_progress.update(task_id=1, advance=50)
        mock_progress.update(task_id=1, advance=50)
        return True

    mock_sync_instance.sync_settings = sync_with_progress
    mocker.patch('obsyncit.obsync_tui.SyncManager', return_value=mock_sync_instance)

    # Mock Table
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Run TUI
    tui.run()

    # Verify progress bars were used correctly
    assert mock_progress.add_task.call_count == 2
    mock_progress.add_task.assert_has_calls([
        call(description="[green]Searching for vaults...", total=None),
        call(description="[green]Syncing vault settings...", total=None)
    ])
    
    # Verify sync progress updates
    assert mock_progress.update.call_count == 3  # 1 for vault discovery completion + 2 for sync progress
    mock_progress.update.assert_has_calls([
        call(1, completed=True),  # Vault discovery completion
        call(task_id=1, advance=50),      # First sync update
        call(task_id=1, advance=50)       # Second sync update
    ])


@pytest.mark.timeout(5)
def test_progress_bar_cleanup_on_error(tui, mock_console, mocker, mock_progress, mock_vault_discovery):
    """Test progress bar cleanup when sync operation fails."""
    # Mock vault discovery
    test_vaults = [Path("/source"), Path("/target")]
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults
    
    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]  # Select first vault for source, first remaining vault for target
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [False, True]  # No dry run, yes proceed

    # Mock sync operation to raise error mid-progress
    mock_sync_instance = Mock()
    def sync_with_error():
        mock_progress.update(task_id=1, advance=50)
        raise ObsyncError("Sync failed", "Test error")

    mock_sync_instance.sync_settings = sync_with_error
    mocker.patch('obsyncit.obsync_tui.SyncManager', return_value=mock_sync_instance)

    # Mock Table
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Run TUI and expect error
    with pytest.raises(SystemExit):
        tui.run()

    # Verify progress bar was cleaned up
    assert mock_progress.__exit__.call_count == 2  # Called once for normal cleanup and once for error
    mock_progress.update.assert_has_calls([
        call(1, completed=True),  # Vault discovery completion
        call(task_id=1, advance=50)  # Sync progress before error
    ])


@pytest.mark.timeout(5)
def test_config_validation_in_tui(tui, mock_console, mocker):
    """Test that TUI properly validates configuration options."""
    # Mock vault discovery
    test_vaults = [Path("/source"), Path("/target")]
    mock_vault_discovery = mocker.patch('obsyncit.obsync_tui.VaultDiscovery')
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults
    mock_vault_discovery.return_value.get_vault_info.return_value = {
        "settings_count": 5,
        "plugin_count": 3
    }
    tui.vault_discovery = mock_vault_discovery.return_value

    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]  # Select first vault for source, first remaining vault for target
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [False, True]  # No dry run, yes proceed

    # Mock sync operation
    mock_sync_instance = Mock()
    mock_sync_instance.sync_settings.return_value = True
    mock_sync = mocker.patch('obsyncit.obsync_tui.SyncManager', return_value=mock_sync_instance)

    # Mock Table
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Run TUI
    tui.run()

    # Verify config was created with correct values
    mock_sync.assert_called_once()
    config = mock_sync.call_args[1]['config']
    assert config.sync.core_settings is True
    assert config.sync.core_plugins is True
    assert config.sync.community_plugins is True
    assert config.sync.themes is True
    assert config.sync.snippets is True
    assert config.sync.dry_run is False


def test_invalid_vault_path_handling(tui, mock_console, mocker):
    """Test handling of invalid vault paths in TUI."""
    # Mock vault discovery
    test_vaults = [Path("/nonexistent/source"), Path("/valid/source"), Path("/valid/target")]
    mock_vault_discovery = mocker.patch('obsyncit.obsync_tui.VaultDiscovery')
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults

    def get_vault_info(vault):
        if str(vault) == "/nonexistent/source":
            raise ObsyncError("Invalid vault path", f"Invalid vault path: {vault}")
        return {
            "name": vault.name,
            "path": str(vault),
            "settings_count": 5,
            "plugin_count": 3
        }
    mock_vault_discovery.return_value.get_vault_info.side_effect = get_vault_info
    tui.vault_discovery = mock_vault_discovery.return_value

    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1"]  # Select the invalid path

    # Mock Table
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Reset mock console
    mock_console.print.reset_mock()

    # Run TUI
    with pytest.raises(SystemExit):
        tui.run()

    # Verify error message
    status_messages = [
        str(call[0][0]) for call in mock_console.print.call_args_list
        if isinstance(call[0][0], str)
    ]
    assert any("Invalid vault path: /nonexistent/source" in msg for msg in status_messages)

    # Verify prompt was called once to select the invalid vault
    assert mock_prompt.call_count == 1


def test_rich_console_styling(tui, mock_console, mocker, mock_vault_discovery):
    """Test that Rich console styling is applied correctly."""
    # Mock vault discovery
    test_vaults = [Path("/source"), Path("/target")]
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults
    
    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]  # Select first vault for source, first remaining vault for target
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [False, True]  # No dry run, yes proceed

    # Mock sync operation
    mock_sync_instance = Mock()
    mock_sync_instance.sync_settings.return_value = True
    mocker.patch('obsyncit.obsync_tui.SyncManager', return_value=mock_sync_instance)

    # Mock Table
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Run TUI
    tui.run()

    # Verify styled output
    styled_calls = [call[0][0] for call in mock_console.print.call_args_list]
    
    # Check header styling
    header_panel = next(call for call in styled_calls if isinstance(call, Panel))
    assert "[bold blue]" in str(header_panel.renderable)
    assert "[dim]" in str(header_panel.renderable)
    
    # Check success message styling
    success_msg = next(msg for msg in styled_calls if isinstance(msg, str) and "Sync completed" in msg)
    assert "[green]" in success_msg
    assert "✓" in success_msg


def test_error_message_formatting(tui, mock_console, mocker, mock_vault_discovery):
    """Test that error messages are properly formatted."""
    # Mock vault discovery
    test_vaults = [Path("/source"), Path("/target")]
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults
    
    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]  # Select first vault for source, first remaining vault for target
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [False, True]  # No dry run, yes proceed

    # Mock sync operation to raise error
    mock_sync_instance = Mock()
    error_msg = "Test error message"
    error_details = "Detailed error information"
    def raise_error():
        raise ObsyncError(error_msg, error_details)
    mock_sync_instance.sync_settings = raise_error
    mocker.patch('obsyncit.obsync_tui.SyncManager', return_value=mock_sync_instance)

    # Mock Table
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Run TUI and expect error
    with pytest.raises(SystemExit):
        tui.run()

    # Verify error message formatting
    error_calls = [
        call[0][0] for call in mock_console.print.call_args_list 
        if isinstance(call[0][0], str) and "[red]" in call[0][0]
    ]
    
    error_output = next(msg for msg in error_calls if error_msg in msg)
    assert "[red]" in error_output
    assert error_msg in error_output
    assert error_details in error_output


def test_preview_table_formatting(tui, mock_console, mocker, mock_vault_discovery):
    """Test that sync preview table is properly formatted."""
    # Mock vault discovery
    test_vaults = [Path("/test/source"), Path("/test/target")]
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults
    mock_vault_discovery.return_value.get_vault_info.return_value = {
        "name": "test",
        "path": "/test",
        "settings_count": 5,
        "plugin_count": 3
    }

    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]  # Select first vault for source, first remaining vault for target
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [False, False]  # No dry run, no proceed

    # Create different mock tables for different purposes
    selection_table = Mock(spec=Table)
    selection_table.add_column = Mock()
    selection_table.add_row = Mock()

    details_table = Mock(spec=Table)
    details_table.add_column = Mock()
    details_table.add_row = Mock()

    preview_table = Mock(spec=Table)
    preview_table.title = "Sync Operation Preview"
    preview_table.add_column = Mock()
    preview_table.add_row = Mock()

    # Mock Table constructor to return different instances based on title
    def create_mock_table(*args, **kwargs):
        title = kwargs.get('title', '')
        if title == "Sync Operation Preview":
            return preview_table
        elif title == "Selected Vault Details":
            return details_table
        else:
            return selection_table

    mocker.patch('obsyncit.obsync_tui.Table', side_effect=create_mock_table)

    # Run TUI
    tui.run()

    # Verify sync preview table formatting (only check the preview table's columns)
    preview_calls = [
        call for call in preview_table.add_column.call_args_list
        if call[0][0] in ["Setting", "Source", "Target"]
    ]
    assert len(preview_calls) == 3
    assert preview_calls == [
        call("Setting", style="cyan"),
        call("Source", style="green"),
        call("Target", style="yellow")
    ]


def test_status_message_formatting(tui, mock_console, mocker):
    """Test formatting of status messages in TUI."""
    # Mock vault discovery
    test_vaults = [Path("/source"), Path("/target")]
    mock_vault_discovery = mocker.patch('obsyncit.obsync_tui.VaultDiscovery')
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults
    mock_vault_discovery.return_value.get_vault_info.return_value = {
        "name": "test",
        "path": "/test",
        "settings_count": 5,
        "plugin_count": 3
    }
    tui.vault_discovery = mock_vault_discovery.return_value

    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]  # Select source and target vaults
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [True, False]  # Yes for dry run, no for proceed

    # Mock Table
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Reset mock console
    mock_console.print.reset_mock()

    # Run TUI
    tui.run()

    # Verify status messages
    status_messages = [
        str(call[0][0]) for call in mock_console.print.call_args_list
        if isinstance(call[0][0], str)
    ]
    assert any("Running in dry run mode" in msg for msg in status_messages)
    assert any("Operation cancelled by user" in msg for msg in status_messages)


def test_discover_vaults(tui, mock_vault_discovery, tmp_path):
    """Test vault discovery in TUI."""
    # Set up mock vaults
    mock_vault = tmp_path / "test_vault"
    mock_vault_discovery.return_value.find_vaults.return_value = [mock_vault]

    # Run discovery
    config = Config()
    vaults = tui.discover_vaults(config)

    # Verify discovery was called with correct parameters
    mock_vault_discovery.assert_called_once_with(
        config.vault.search_path,
        config.vault.search_depth
    )
    assert vaults == [mock_vault]


def test_select_vault_empty_list(tui, mock_console):
    """Test handling of empty vault list."""
    # Reset mock console
    mock_console.print.reset_mock()

    # Try to select from empty list
    result = tui.select_vault([], "Select vault:")

    # Verify error message
    status_messages = [
        str(call[0][0]) for call in mock_console.print.call_args_list
        if isinstance(call[0][0], str)
    ]
    assert any("No vaults found" in msg for msg in status_messages), "No vaults found message not shown"
    assert result is None


def test_select_vault_single_vault(tui, mock_console, mock_vault_discovery, tmp_path, mocker):
    """Test vault selection with a single vault."""
    # Mock vault and its info
    vault = tmp_path / "test_vault"
    mock_vault_discovery.get_vault_info.return_value = {
        "name": "test_vault",
        "path": str(vault),
        "settings_count": 5,
        "plugin_count": 3
    }

    # Mock Table
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Mock user input
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.return_value = "1"

    result = tui.select_vault([vault], "Select vault:")
    assert result == vault


def test_select_vault_multiple_vaults(tui, mock_console, mock_vault_discovery, tmp_path, mocker):
    """Test vault selection with multiple vaults."""
    # Create mock vaults
    vault1 = tmp_path / "vault1"
    vault2 = tmp_path / "vault2"
    vaults = [vault1, vault2]

    # Mock vault info
    def get_vault_info(vault):
        return {
            "name": vault.name,
            "path": str(vault),
            "settings_count": 5,
            "plugin_count": 3
        }
    mock_vault_discovery.get_vault_info.side_effect = get_vault_info

    # Mock Table
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Mock user input
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.return_value = "2"

    result = tui.select_vault(vaults, "Select vault:")
    assert result == vault2


def test_select_vault_cancel(tui, mock_console, mock_vault_discovery, tmp_path, mocker):
    """Test cancelling vault selection."""
    vault = tmp_path / "test_vault"
    mock_vault_discovery.get_vault_info.return_value = {
        "name": "test_vault",
        "path": str(vault),
        "settings_count": 5,
        "plugin_count": 3
    }

    # Mock Table
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Mock user input to quit
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.return_value = "q"

    result = tui.select_vault([vault], "Select vault:")
    assert result is None


def test_select_vault_invalid_input(tui, mock_console, mocker):
    """Test handling of invalid vault selection input."""
    # Mock vault discovery
    test_vaults = [Path("/test_vault1"), Path("/test_vault2")]
    mock_vault_discovery = mocker.patch('obsyncit.obsync_tui.VaultDiscovery')
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults
    mock_vault_discovery.return_value.get_vault_info.return_value = {
        "name": "test",
        "path": "/test",
        "settings_count": 5,
        "plugin_count": 3
    }
    tui.vault_discovery = mock_vault_discovery.return_value

    # Mock Rich's prompt to return invalid input first, then valid
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["invalid", "1"]

    # Mock Table
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Reset mock console
    mock_console.print.reset_mock()

    # Try to select vault
    result = tui.select_vault(test_vaults, "Select vault:")

    # Verify error message for invalid input
    status_messages = [
        str(call[0][0]) for call in mock_console.print.call_args_list
        if isinstance(call[0][0], str)
    ]
    assert any("Invalid selection. Please enter a number from the list." in msg for msg in status_messages), "Invalid selection message not shown"
    assert result == test_vaults[0]  # Should eventually select first vault

    # Verify prompt was called twice (once for invalid, once for valid)
    assert mock_prompt.call_count == 2


def test_get_vault_paths_no_vaults(tui, mock_vault_discovery):
    """Test vault path selection when no vaults are found."""
    mock_vault_discovery.return_value.find_vaults.return_value = []
    config = Config()

    source, target = tui.get_vault_paths(config)
    assert source is None
    assert target is None
    tui.console.print.assert_called_with("[yellow]No vaults found. Please check your search path.[/yellow]")


def test_get_vault_paths_single_vault(tui, mock_console, mock_vault_discovery, tmp_path, mocker):
    """Test vault path selection with only one vault."""
    # Mock vault discovery
    vault = tmp_path / "test_vault"
    mock_vault_discovery.return_value.find_vaults.return_value = [vault]
    mock_vault_discovery.return_value.get_vault_info.return_value = {
        "name": "test_vault",
        "path": str(vault),
        "settings_count": 5,
        "plugin_count": 3
    }

    # Mock prompt
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.return_value = "1"

    config = Config()
    source, target = tui.get_vault_paths(config)
    assert source is None
    assert target is None
    mock_console.print.assert_any_call("[yellow]No other vaults available as targets[/yellow]")


def test_get_vault_paths_success(tui, mock_vault_discovery, tmp_path, mocker):
    """Test successful vault path selection."""
    # Create mock vaults
    vault1 = tmp_path / "vault1"
    vault2 = tmp_path / "vault2"
    mock_vault_discovery.return_value.find_vaults.return_value = [vault1, vault2]

    # Mock vault info
    def get_vault_info(vault):
        return {
            "name": vault.name,
            "path": str(vault),
            "settings_count": 5,
            "plugin_count": 3
        }
    mock_vault_discovery.get_vault_info.side_effect = get_vault_info

    # Mock user input for source and target selection
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]  # Select first vault as source, first remaining vault as target

    config = Config()
    source, target = tui.get_vault_paths(config)

    assert source == str(vault1)
    assert target == str(vault2)


def test_run_unexpected_error(tui, mock_console, mocker, mock_progress, mock_vault_discovery):
    """Test handling of unexpected exceptions."""
    # Mock logging
    mock_logging = mocker.patch('obsyncit.obsync_tui.logging')
    
    # Mock vault discovery
    test_vaults = [Path("/source"), Path("/target")]
    mock_vault_discovery.return_value.find_vaults.return_value = test_vaults
    
    # Mock Rich's prompts
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1"]  # Select first vault for source, first remaining vault for target
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [False, True]  # No dry run, yes proceed

    # Mock sync operation to raise unexpected error
    unexpected_error = RuntimeError("Unexpected test error")
    mock_sync_instance = Mock()
    mock_sync_instance.sync_settings = Mock(side_effect=unexpected_error)
    mocker.patch('obsyncit.obsync_tui.SyncManager', return_value=mock_sync_instance)

    # Mock Table
    mock_table = Mock(spec=Table)
    mock_table.add_column = Mock()
    mock_table.add_row = Mock()
    mocker.patch('obsyncit.obsync_tui.Table', return_value=mock_table)

    # Run TUI and check exit code
    with pytest.raises(SystemExit) as exc_info:
        tui.run()
    assert exc_info.value.code == 1

    # Verify error message was printed
    error_message = f"[red]Error: {str(unexpected_error)}[/red]"
    mock_console.print.assert_any_call(error_message)
    
    # Verify logging
    mock_logging.exception.assert_called_once_with("Unexpected error")