"""
Obsidian Settings Sync - Text User Interface.

This module provides a Text User Interface (TUI) for the ObsyncIt tool,
allowing users to interactively synchronize settings between Obsidian vaults.
It uses the Rich library for terminal formatting and display.

Classes:
    Status: Enumeration of operation status indicators
    Style: Enumeration of UI style definitions
    VaultPaths: Data container for vault path information
    ProgressInterface: Abstract base class for progress indicators
    SyncProgress: Concrete progress indicator using Rich
    MockProgress: Mock progress indicator for testing
    ObsidianSyncTUI: Main TUI application class

Example:
    >>> from obsyncit.obsync_tui import ObsidianSyncTUI
    >>> tui = ObsidianSyncTUI()
    >>> tui.run()
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, List, Tuple, Type, BaseException, TracebackType
import argparse

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    TaskID,
)
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.theme import Theme

from obsyncit.sync import SyncManager, SyncResult
from obsyncit.vault_discovery import VaultDiscovery
from obsyncit.schemas import Config
from obsyncit.errors import ObsyncError
from obsyncit.logger import setup_logging

logger = logging.getLogger(__name__)


class Status(Enum):
    """Status indicators for various operations.
    
    This enumeration defines Unicode characters used to indicate
    the status of various operations in the TUI.
    
    Attributes:
        SUCCESS: Checkmark indicating successful completion
        FAILURE: X mark indicating failure
        PENDING: Empty circle indicating pending operation
        RUNNING: Filled circle indicating operation in progress
    """
    SUCCESS = "✓"
    FAILURE = "✗"
    PENDING = "○"
    RUNNING = "●"


class Style(Enum):
    """Style definitions for UI elements.
    
    This enumeration defines color styles used throughout the TUI
    for consistent visual feedback.
    
    Attributes:
        SUCCESS: Color for successful operations (green)
        ERROR: Color for errors and failures (red)
        WARNING: Color for warnings and cautions (yellow)
        INFO: Color for general information (blue)
        DIM: Color for less important text (dim)
    """
    SUCCESS = "green"
    ERROR = "red"
    WARNING = "yellow"
    INFO = "blue"
    DIM = "dim"


@dataclass
class VaultPaths:
    """Holds information about selected vault paths.
    
    This dataclass stores paths and existence status for source
    and target Obsidian vaults during sync operations.
    
    Attributes:
        source: Path to the source vault
        target: Path to the target vault
        source_exists: Whether the source vault exists
        target_exists: Whether the target vault exists
    
    Example:
        >>> paths = VaultPaths(
        ...     source=Path("/path/to/source"),
        ...     target=Path("/path/to/target"),
        ...     source_exists=True,
        ...     target_exists=True
        ... )
    """
    source: Path
    target: Path
    source_exists: bool = False
    target_exists: bool = False


class ProgressInterface:
    """Abstract base class for progress indicators.
    
    This class defines the interface for progress indicators used during
    synchronization operations. It provides context manager support and
    methods for starting, stopping, and updating progress status.
    
    Example:
        >>> with ProgressInterface() as progress:
        ...     progress.update("Syncing files...")
        ...     # Perform sync operation
        ...     progress.update("Backup complete", completed=True)
    
    Note:
        This is an abstract base class. Concrete implementations must override
        the start(), stop(), and update() methods.
    """

    def __enter__(self) -> "ProgressInterface":
        """Enter the context manager.
        
        Returns:
            ProgressInterface: The progress interface instance for use in the context.
        """
        self.start()
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], 
                 exc_val: Optional[BaseException], 
                 exc_tb: Optional[TracebackType]) -> None:
        """Exit the context manager.
        
        Args:
            exc_type: The type of the exception that was raised, if any
            exc_val: The instance of the exception that was raised, if any
            exc_tb: The traceback of the exception that was raised, if any
        """
        self.stop()

    def start(self) -> None:
        """Start the progress indicator.
        
        This method should initialize any necessary resources and
        display the initial progress state.
        
        Raises:
            NotImplementedError: This is an abstract method that must be implemented
                by concrete subclasses.
        """
        raise NotImplementedError

    def stop(self) -> None:
        """Stop the progress indicator.
        
        This method should clean up any resources and finalize the
        progress display.
        
        Raises:
            NotImplementedError: This is an abstract method that must be implemented
                by concrete subclasses.
        """
        raise NotImplementedError

    def update(self, description: str, completed: bool = False) -> None:
        """Update progress status.
        
        Args:
            description: A description of the current operation
            completed: Whether the operation is complete
        
        Raises:
            NotImplementedError: This is an abstract method that must be implemented
                by concrete subclasses.
        """
        raise NotImplementedError


class SyncProgress(ProgressInterface):
    """Manages progress indication during sync operations.
    
    This class provides a concrete implementation of the ProgressInterface
    using Rich's Progress component to display real-time sync status in
    the terminal.
    
    Attributes:
        console: The Rich console instance for output
        progress: The Rich progress bar instance
        task_id: The ID of the current progress task
    
    Example:
        >>> from rich.console import Console
        >>> console = Console()
        >>> with SyncProgress(console) as progress:
        ...     progress.update("Scanning vault...")
        ...     # Perform sync operations
        ...     progress.update("Syncing plugins...", completed=False)
        ...     # More sync operations
        ...     progress.update("Sync complete!", completed=True)
    """

    def __init__(self, console: Console):
        """Initialize the sync progress indicator.
        
        Args:
            console: The Rich console instance to use for output
        """
        self.console = console
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        )
        self.task_id: Optional[TaskID] = None

    def start(self) -> None:
        """Start displaying the progress indicator.
        
        This method initializes the Rich progress bar and displays it
        in the terminal.
        """
        self.progress.start()

    def stop(self) -> None:
        """Stop displaying the progress indicator.
        
        This method cleans up the progress display and removes it
        from the terminal.
        """
        self.progress.stop()

    def update(self, description: str, completed: bool = False) -> None:
        """Update the sync progress status.
        
        This method updates the progress display with a new description
        and optionally marks the task as completed.
        
        Args:
            description: A description of the current sync operation
            completed: Whether the sync operation is complete
        """
        if self.task_id is None:
            self.task_id = self.progress.add_task(description, total=None)
        self.progress.update(self.task_id, description=description, completed=completed)


class MockProgress(ProgressInterface):
    """Mock progress indicator for testing.
    
    This class provides a test double for the ProgressInterface,
    recording all operations for verification in tests.
    
    Attributes:
        started: Whether start() has been called
        stopped: Whether stop() has been called
        updates: List of (description, completed) tuples recording update calls
    
    Example:
        >>> progress = MockProgress()
        >>> progress.start()
        >>> progress.update("Testing...", completed=False)
        >>> progress.update("Done!", completed=True)
        >>> progress.stop()
        >>> assert len(progress.updates) == 2
        >>> assert progress.started and progress.stopped
    """

    def __init__(self):
        """Initialize the mock progress indicator."""
        self.started = False
        self.stopped = False
        self.updates: List[tuple[str, bool]] = []

    def start(self) -> None:
        """Record that the progress indicator was started."""
        self.started = True

    def stop(self) -> None:
        """Record that the progress indicator was stopped."""
        self.stopped = True

    def update(self, description: str, completed: bool = False) -> None:
        """Record a progress update.
        
        Args:
            description: Description of the current operation
            completed: Whether the operation is complete
        """
        self.updates.append((description, completed))


class ObsidianSyncTUI:
    """Text User Interface for Obsidian Settings Sync.
    
    This class provides the main TUI application for synchronizing
    Obsidian vault settings. It handles vault discovery, user interaction,
    and sync operations with progress display.
    
    Attributes:
        console: Rich console for formatted output
        vault_discovery: VaultDiscovery instance for finding vaults
        config: Configuration settings
        DEFAULT_SYNC_ITEMS: List of items to sync by default
    
    Example:
        >>> tui = ObsidianSyncTUI()
        >>> success = tui.run()
        >>> if success:
        ...     print("Sync completed successfully!")
    """

    # Default items to sync
    DEFAULT_SYNC_ITEMS = [
        # Core settings
        "app.json",
        "appearance.json",
        "hotkeys.json",
        "types.json",
        "templates.json",
        
        # Plugin settings
        "core-plugins.json",
        "community-plugins.json",
        "core-plugins-migration.json",
        "plugins",
        "icons",
        
        # Additional content
        "themes",
        "snippets",
    ]

    def __init__(
        self,
        search_path: Optional[Path] = None,
        progress_factory: Optional[type[ProgressInterface]] = None
    ):
        """Initialize the TUI application.
        
        Args:
            search_path: Optional custom path to search for Obsidian vaults.
                       Defaults to user's home directory if not specified.
            progress_factory: Optional factory class for creating progress indicators.
                            Defaults to SyncProgress. Useful for testing with MockProgress.
        """
        self.console = Console(theme=Theme({
            "info": Style.INFO.value,
            "warning": Style.WARNING.value,
            "error": Style.ERROR.value,
            "success": Style.SUCCESS.value,
        }))
        # Use home directory as default search path
        default_path = Path.home()
        self.vault_discovery = VaultDiscovery(search_path or default_path)
        self.config = Config()
        self._progress_factory = progress_factory or SyncProgress

    def create_progress(self) -> ProgressInterface:
        """Create a new progress indicator instance.
        
        This method uses the configured progress_factory to create
        either a real progress indicator for the TUI or a mock one
        for testing.
        
        Returns:
            A new progress indicator instance
        """
        if self._progress_factory == SyncProgress:
            return self._progress_factory(self.console)
        return self._progress_factory()

    def display_header(self) -> None:
        """Display the application header.
        
        Shows a styled panel containing the application title and description.
        """
        self.console.print(Panel(
            "[bold]Obsidian Settings Sync[/bold]\n"
            "Synchronize settings between Obsidian vaults",
            style=Style.INFO.value,
        ))

    def get_vault_paths(self) -> VaultPaths:
        """Discover and let user select source and target vaults.
        
        This method:
        1. Searches for available Obsidian vaults
        2. Displays them in a table
        3. Prompts user to select source and target vaults
        4. Validates the selections
        
        Returns:
            VaultPaths object containing selected source and target paths
            
        Raises:
            SystemExit: If no vaults are found or if user makes invalid selections
        """
        with self.create_progress() as progress:
            progress.update("Searching for vaults...")
            available_vaults = self.vault_discovery.find_vaults()
            progress.update("Search complete", completed=True)

        if not available_vaults:
            self.console.print(
                f"[{Style.ERROR.value}]No Obsidian vaults found[/]"
            )
            sys.exit(1)

        vault_table = Table(title="Available Vaults")
        vault_table.add_column("Number", style=Style.INFO.value)
        vault_table.add_column("Path", style=Style.DIM.value)
        
        for i, vault in enumerate(available_vaults, 1):
            vault_table.add_row(str(i), str(vault))
        
        self.console.print(vault_table)

        source_idx = int(Prompt.ask(
            f"[{Style.INFO.value}]Select source vault (1-{len(available_vaults)})[/]"
        )) - 1

        if not (0 <= source_idx < len(available_vaults)):
            self.console.print(
                f"[{Style.ERROR.value}]Invalid selection. Please choose a number between 1 and {len(available_vaults)}[/]"
            )
            sys.exit(1)

        source_vault = available_vaults[source_idx]

        while True:
            target_idx = int(Prompt.ask(
                f"[{Style.INFO.value}]Select target vault (1-{len(available_vaults)})[/]"
            )) - 1

            if not (0 <= target_idx < len(available_vaults)):
                self.console.print(
                    f"[{Style.ERROR.value}]Invalid selection. Please choose a number between 1 and {len(available_vaults)}[/]"
                )
                continue

            if target_idx == source_idx:
                self.console.print(
                    f"[{Style.ERROR.value}]Source and target vaults must be different. Please select a different vault.[/]"
                )
                continue

            break

        target_vault = available_vaults[target_idx]

        return VaultPaths(
            source=source_vault,
            target=target_vault,
            source_exists=source_vault.exists(),
            target_exists=target_vault.exists(),
        )

    def display_sync_preview(self, paths: VaultPaths) -> None:
        """Display a preview of the sync operation.
        
        Shows a table with source and target vault paths and their
        existence status.
        
        Args:
            paths: VaultPaths object containing the vault paths to preview
        """
        table = Table(
            title="Sync Operation Preview",
            show_header=True,
            header_style=Style.INFO.value,
        )
        table.add_column("Setting", style=Style.INFO.value)
        table.add_column("Path", style=Style.DIM.value)
        table.add_column("Status", justify="center")

        table.add_row(
            "Source Vault",
            str(paths.source),
            f"[{Style.SUCCESS.value if paths.source_exists else Style.ERROR.value}]"
            f"{Status.SUCCESS.value if paths.source_exists else Status.FAILURE.value}",
        )
        table.add_row(
            "Target Vault",
            str(paths.target),
            f"[{Style.SUCCESS.value if paths.target_exists else Style.ERROR.value}]"
            f"{Status.SUCCESS.value if paths.target_exists else Status.FAILURE.value}",
        )

        self.console.print(table)

    def display_sync_results(self, result: SyncResult, dry_run: bool = True) -> None:
        """Display the results of a sync operation.
        
        Shows a table with the results of the sync operation, including:
        - Successfully synced items
        - Any errors that occurred
        - Overall operation status
        
        Args:
            result: The sync operation result object
            dry_run: Whether this was a dry run
        """
        operation = "Dry run" if dry_run else "Sync"
        
        if result.success:
            # Create results table
            table = Table(
                title=f"{operation} Results",
                show_header=True,
                header_style=Style.INFO.value,
            )
            table.add_column("Item", style=Style.INFO.value)
            table.add_column("Status", style=Style.SUCCESS.value)
            table.add_column("Details", style=Style.DIM.value)

            # Add sync details
            if result.items_synced:
                for item in result.items_synced:
                    table.add_row(
                        str(item),
                        Status.SUCCESS.value,
                        "Successfully synced"
                    )
            else:
                table.add_row(
                    "No items",
                    Status.PENDING.value,
                    "No items were specified for sync"
                )

            self.console.print(table)
            self.console.print(
                f"[{Style.SUCCESS.value}]"
                f"{Status.SUCCESS.value} "
                f"{operation} completed successfully![/]"
            )
        else:
            error_table = Table(
                title=f"{operation} Errors",
                show_header=True,
                header_style=Style.ERROR.value,
            )
            error_table.add_column("Item", style=Style.ERROR.value)
            error_table.add_column("Error", style=Style.DIM.value)

            if result.errors:
                for item, error in result.errors.items():
                    error_table.add_row(str(item), str(error))
            else:
                error_table.add_row("General", str(result))

            self.console.print(error_table)
            self.console.print(
                f"[{Style.ERROR.value}]"
                f"{Status.FAILURE.value} "
                f"{operation} failed![/]"
            )

    def confirm_sync(self, dry_run: bool = True) -> Tuple[bool, bool]:
        """Get user confirmation for the sync operation.
        
        If dry_run is True, first asks if the user wants to perform a dry run.
        Then asks for confirmation to proceed with the selected operation.
        
        Args:
            dry_run: Whether to suggest a dry run first

        Returns:
            Tuple of (should_proceed, is_dry_run) where:
            - should_proceed: Whether to proceed with the operation
            - is_dry_run: Whether to perform a dry run
        """
        logger.debug("Entering confirm_sync(dry_run=%s)", dry_run)
        
        want_dry_run = False
        if dry_run:
            want_dry_run = Confirm.ask(
                f"\n[{Style.WARNING.value}]Would you like to perform a dry run first?[/]",
                default=True,
            )
            logger.debug("User wants dry run: %s", want_dry_run)

        should_proceed = Confirm.ask(
            f"\n[{Style.WARNING.value}]Ready to proceed with "
            f"{'dry run' if want_dry_run else 'sync'}?[/]",
            default=True,
        )
        logger.debug("User wants to proceed: %s", should_proceed)

        if not should_proceed:
            self.console.print(f"[{Style.WARNING.value}]Operation cancelled by user[/]")
            logger.debug("Operation cancelled by user")
            return False, want_dry_run

        logger.debug("Returning (proceed=%s, dry_run=%s)", True, want_dry_run)
        return True, want_dry_run

    def run(self) -> bool:
        """Run the TUI application.
        
        This is the main entry point for the TUI application. It:
        1. Displays the application header
        2. Discovers and lets user select vaults
        3. Shows a sync preview
        4. Gets user confirmation
        5. Performs the sync operation
        6. Shows the results
        
        If a dry run is performed successfully, offers to perform
        the actual sync operation.
        
        Returns:
            bool: True if the operation was successful, False otherwise
        
        Raises:
            Any exceptions from underlying operations are caught,
            logged, and result in a return value of False
        """
        try:
            logger.debug("Starting TUI application")
            self.display_header()

            paths = self.get_vault_paths()
            self.display_sync_preview(paths)

            logger.debug("Getting confirmation for sync")
            should_proceed, is_dry_run = self.confirm_sync()
            if not should_proceed:
                logger.debug("User cancelled operation")
                return False

            logger.debug("Configuring sync_manager with dry_run=%s", is_dry_run)
            self.config.sync.dry_run = is_dry_run

            sync_mgr = SyncManager(paths.source, paths.target, self.config)
            
            with self.create_progress() as progress:
                progress.update("[green]Syncing vault settings...")
                logger.debug("Calling sync_settings()")
                result = sync_mgr.sync_settings(self.DEFAULT_SYNC_ITEMS)

            self.display_sync_results(result, is_dry_run)

            if result.success and is_dry_run:
                logger.debug("Dry run succeeded, offering actual sync")
                should_proceed, _ = self.confirm_sync(dry_run=False)
                if should_proceed:
                    self.config.sync.dry_run = False
                    with self.create_progress() as progress:
                        progress.update("[green]Syncing vault settings...")
                        logger.debug("Calling sync_settings() for actual sync")
                        result = sync_mgr.sync_settings(self.DEFAULT_SYNC_ITEMS)
                        self.display_sync_results(result, dry_run=False)

            logger.debug("Operation complete, returning success=%s", result.success)
            return result.success

        except Exception as e:
            logger.error("Error in TUI application", exc_info=True)
            self.console.print(f"[{Style.ERROR.value}]Error: {str(e)}[/]")
            if isinstance(e, ObsyncError):
                self.console.print(f"[{Style.DIM.value}]Details: {e.details}[/]")
            self.console.print_exception()
            return False


def main() -> None:
    """Entry point for the TUI application."""
    parser = argparse.ArgumentParser(
        description="Interactive TUI for Obsidian Settings Sync",
    )
    parser.add_argument(
        "--search-path",
        type=Path,
        help="Custom path to search for Obsidian vaults",
    )
    args = parser.parse_args()

    setup_logging(Config())
    tui = ObsidianSyncTUI(search_path=args.search_path)
    sys.exit(0 if tui.run() else 1)


if __name__ == "__main__":
    main()