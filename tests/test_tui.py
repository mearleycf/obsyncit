"""Tests for Terminal User Interface functionality."""

import time
import pytest
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from obsyncit.obsync_tui import ObsidianSyncTUI, Status, Style, VaultPaths, MockProgress
from tests.test_utils import create_test_vault


def get_time():
    """Get current time in seconds."""
    return time.time()


class MockConsole(Mock):
    """Mock console that supports context manager protocol."""
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return None


@pytest.fixture
def mock_console():
    """Create a mock console."""
    console = MockConsole(spec=Console)
    console.print = Mock()
    console.is_terminal = True
    console.is_interactive = True
    console.height = 24
    console.width = 80
    console.color_system = "auto"
    console.get_time = get_time
    console.is_jupyter = False
    console.clear_live = Mock()
    console.show_cursor = Mock()
    console.set_live = Mock()
    console.push_render_hook = Mock()
    return console


@pytest.fixture
def sample_vaults(clean_dir):
    """Create test vaults for TUI testing."""
    source = create_test_vault(clean_dir / "source")
    target = create_test_vault(clean_dir / "target")
    return [source, target]


@pytest.fixture
def tui(mock_console):
    """Create a TUI instance with mocked components."""
    tui = ObsidianSyncTUI(progress_factory=MockProgress)
    tui.console = mock_console
    tui.vault_discovery.find_vaults = Mock()
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
    # Mock vault discovery
    test_vaults = [Path("/test/vault1"), Path("/test/vault2")]
    tui.vault_discovery.find_vaults.return_value = test_vaults
    
    # Mock Prompt.ask
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "2"]
    
    # Call the method
    paths = tui.get_vault_paths()
    
    # Verify results
    assert mock_prompt.call_count == 2
    assert paths.source == test_vaults[0]
    assert paths.target == test_vaults[1]


def test_get_vault_paths_same_selection(tui, mocker):
    """Test selecting same vault for source and target."""
    test_vaults = [Path("/test/vault1"), Path("/test/vault2")]
    tui.vault_discovery.find_vaults.return_value = test_vaults
    
    # Mock Prompt.ask to first try selecting same vault, then different
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_prompt.side_effect = ["1", "1", "2"]
    
    paths = tui.get_vault_paths()
    
    assert mock_prompt.call_count == 3  # Called extra time due to retry
    assert paths.source == test_vaults[0]
    assert paths.target == test_vaults[1]


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


def test_confirm_sync(tui, mocker):
    """Test sync confirmation flow."""
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_confirm.side_effect = [True, True]  # dry_run=True, proceed=True
    
    result = tui.confirm_sync()
    
    assert mock_confirm.call_count == 2
    assert result is True


def test_sync_success(tui, sample_vaults, mocker):
    """Test successful sync operation."""
    # Mock vault discovery
    tui.vault_discovery.find_vaults.return_value = sample_vaults
    
    # Mock Prompt.ask and Confirm.ask
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_prompt.side_effect = ["1", "2"]  # vault selections
    mock_confirm.side_effect = [True, True, False]  # dry_run=True, proceed=True, no actual sync
    
    # Mock sync manager
    with mocker.patch('obsyncit.obsync_tui.SyncManager') as mock_sync:
        mock_instance = mock_sync.return_value
        mock_instance.sync_settings.return_value = Mock(
            success=True,
            synced_items={"test.json": "Updated"},
            items_failed=[],
            errors={},
            summary="Sync successful"
        )
        
        # Run TUI
        result = tui.run()
        assert result is True
        
        # Verify sync was called
        mock_instance.sync_settings.assert_called_once()
        
        # Verify results table was displayed
        tables_printed = 0
        for call_args in tui.console.print.call_args_list:
            args = call_args[0]
            if isinstance(args[0], Table) and args[0].title == "Dry run Results":
                tables_printed += 1
        assert tables_printed > 0


def test_sync_failure(tui, sample_vaults, mocker):
    """Test sync failure handling."""
    # Mock vault discovery
    tui.vault_discovery.find_vaults.return_value = sample_vaults
    
    # Mock Prompt.ask and Confirm.ask
    mock_prompt = mocker.patch('obsyncit.obsync_tui.Prompt.ask')
    mock_confirm = mocker.patch('obsyncit.obsync_tui.Confirm.ask')
    mock_prompt.side_effect = ["1", "2"]
    mock_confirm.side_effect = [True, True]
    
    # Mock sync manager
    with mocker.patch('obsyncit.obsync_tui.SyncManager') as mock_sync:
        mock_instance = mock_sync.return_value
        mock_instance.sync_settings.return_value = Mock(
            success=False,
            synced_items={},
            items_failed=["test.json"],
            errors={"test.json": "Failed to copy"},
            summary="Sync failed"
        )
        
        # Run TUI
        result = tui.run()
        assert result is False
        
        # Verify error table was displayed
        error_tables = 0
        for call_args in tui.console.print.call_args_list:
            args = call_args[0]
            if isinstance(args[0], Table) and args[0].title == "Dry run Errors":
                error_tables += 1
        assert error_tables > 0


def test_no_vaults_found(tui):
    """Test handling when no vaults found."""
    tui.vault_discovery.find_vaults.return_value = []
    
    # Run TUI and verify it exits with the right message
    with pytest.raises(SystemExit) as exc_info:
        tui.run()
    
    assert exc_info.value.code == 1
    
    # Verify error message was printed
    assert any(
        "[red]No Obsidian vaults found" in str(call_args[0][0])
        for call_args in tui.console.print.call_args_list
    )