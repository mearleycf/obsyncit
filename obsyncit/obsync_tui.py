#!/usr/bin/env python3

"""
Obsidian Settings Sync - Text User Interface.

This module provides a rich terminal user interface for the Obsidian Settings
Sync tool. It offers a more interactive way to use the tool, with features like:
- Interactive prompts for vault paths
- Visual sync operation preview
- Progress indicators
- Rich error formatting and tracebacks
- Colorized output
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any
import argparse

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    ProgressColumn,
    TaskID,
)
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.theme import Theme

from obsyncit.sync import SyncManager
from obsyncit.vault_discovery import VaultDiscovery
from obsyncit.schemas import Config
from obsyncit.errors import ObsyncError
from obsyncit.logger import setup_logging


class Status(Enum):
    """Status indicators for various operations."""
    SUCCESS = "✓"
    FAILURE = "✗"
    PENDING = "○"
    RUNNING = "●"


class Style(Enum):
    """Style definitions for UI elements."""
    SUCCESS = "green"
    ERROR = "red"
    WARNING = "yellow"
    INFO = "blue"
    DIM = "dim"


@dataclass
class VaultPaths:
    """Holds information about selected vault paths."""
    source: Path
    target: Path
    source_exists: bool = False
    target_exists: bool = False


class ProgressInterface:
    """Abstract base class for progress indicators."""

    def __enter__(self) -> "ProgressInterface":
        """Enter the context manager."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context manager."""
        self.stop()

    def start(self) -> None:
        """Start the progress indicator."""
        raise NotImplementedError

    def stop(self) -> None:
        """Stop the progress indicator."""
        raise NotImplementedError

    def update(self, description: str, completed: bool = False) -> None:
        """Update progress status.
        
        Args:
            description: New progress description
            completed: Whether the task is completed
        """
        raise NotImplementedError


class SyncProgress(ProgressInterface):
    """Manages progress indication during sync operations."""

    def __init__(self, console: Console):
        """Initialize progress manager.
        
        Args:
            console: Rich console instance
        """
        self.console = console
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        )
        self.task_id: Optional[TaskID] = None

    def start(self) -> None:
        """Start the progress display."""
        self.progress.start()

    def stop(self) -> None:
        """Stop the progress display."""
        self.progress.stop()

    def update(self, description: str, completed: bool = False) -> None:
        """Update progress status.
        
        Args:
            description: New progress description
            completed: Whether the task is completed
        """
        if self.task_id is None:
            self.task_id = self.progress.add_task(description, total=None)
        self.progress.update(self.task_id, description=description, completed=completed)


class MockProgress(ProgressInterface):
    """Mock progress indicator for testing."""

    def __init__(self):
        """Initialize mock progress."""
        self.started = False
        self.stopped = False
        self.updates: List[tuple[str, bool]] = []

    def start(self) -> None:
        """Start the mock progress."""
        self.started = True

    def stop(self) -> None:
        """Stop the mock progress."""
        self.stopped = True

    def update(self, description: str, completed: bool = False) -> None:
        """Record a progress update.
        
        Args:
            description: Progress description
            completed: Whether the task is completed
        """
        self.updates.append((description, completed))


class ObsidianSyncTUI:
    """Text User Interface for Obsidian Settings Sync."""

    def __init__(
        self,
        search_path: Optional[Path] = None,
        progress_factory: Optional[type[ProgressInterface]] = None
    ):
        """Initialize the TUI.
        
        Args:
            search_path: Optional path to search for vaults. Defaults to current directory.
            progress_factory: Optional factory for creating progress indicators.
                           Defaults to SyncProgress.
        """
        self.console = Console(theme=Theme({
            "info": Style.INFO.value,
            "warning": Style.WARNING.value,
            "error": Style.ERROR.value,
            "success": Style.SUCCESS.value,
        }))
        self.vault_discovery = VaultDiscovery(search_path or Path.cwd())
        self.config = Config()
        self._progress_factory = progress_factory or SyncProgress

    def create_progress(self) -> ProgressInterface:
        """Create a progress indicator instance.
        
        Returns:
            A new progress indicator instance
        """
        if self._progress_factory == SyncProgress:
            return self._progress_factory(self.console)
        return self._progress_factory()

    def display_header(self) -> None:
        """Display application header."""
        self.console.print(Panel(
            "[bold]Obsidian Settings Sync[/bold]\n"
            "Synchronize settings between Obsidian vaults",
            style=Style.INFO.value,
        ))

    def get_vault_paths(self) -> VaultPaths:
        """Get source and target vault paths through interactive prompts.
        
        Returns:
            VaultPaths containing selected paths and their status
        
        Raises:
            SystemExit: If no vaults are found or if an invalid selection is made
        """
        with self.create_progress() as progress:
            progress.update("[green]Searching for vaults...")
            available_vaults = self.vault_discovery.find_vaults()
            progress.update("[green]Search complete", completed=True)

        if not available_vaults:
            self.console.print(
                f"[{Style.ERROR.value}]No Obsidian vaults found[/]"
            )
            sys.exit(1)

        # Display available vaults
        vault_table = Table(title="Available Vaults")
        vault_table.add_column("Number", style=Style.INFO.value)
        vault_table.add_column("Path", style=Style.DIM.value)
        
        for i, vault in enumerate(available_vaults, 1):
            vault_table.add_row(str(i), str(vault))
        
        self.console.print(vault_table)

        # Get source vault
        source_idx = int(Prompt.ask(
            f"[{Style.INFO.value}]Select source vault (1-{len(available_vaults)})[/]"
        )) - 1

        if not (0 <= source_idx < len(available_vaults)):
            self.console.print(
                f"[{Style.ERROR.value}]Invalid selection. Please choose a number between 1 and {len(available_vaults)}[/]"
            )
            sys.exit(1)

        source_vault = available_vaults[source_idx]

        # Get target vault
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
        """Display preview of sync operation.
        
        Args:
            paths: VaultPaths containing source and target information
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

    def confirm_sync(self, dry_run: bool = True) -> bool:
        """Get user confirmation for the sync operation.
        
        Args:
            dry_run: Whether to suggest a dry run first

        Returns:
            True if the user confirms, False otherwise
        """
        if dry_run:
            dry_run_confirmed = Confirm.ask(
                f"\n[{Style.WARNING.value}]Would you like to perform a dry run first?[/]",
                default=True,
            )
        else:
            dry_run_confirmed = False

        proceed = Confirm.ask(
            f"\n[{Style.WARNING.value}]Ready to proceed with "
            f"{'dry run' if dry_run_confirmed else 'sync'}?[/]",
            default=True,
        )

        if not proceed:
            self.console.print(f"[{Style.WARNING.value}]Operation cancelled by user[/]")
            return False

        return dry_run_confirmed

    def display_sync_results(self, result: Any, dry_run: bool = True) -> None:
        """Display the results of a sync operation.
        
        Args:
            result: The sync operation result
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
            if result.synced_items:
                for item, details in result.synced_items.items():
                    table.add_row(
                        str(item),
                        Status.SUCCESS.value,
                        str(details) if details else "No changes needed"
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

    def run(self) -> bool:
        """Run the TUI application.
        
        Returns:
            True if sync was successful, False otherwise
        """
        try:
            self.display_header()

            # Get vault paths and preview
            paths = self.get_vault_paths()
            self.display_sync_preview(paths)

            # Get confirmation and dry run preference
            dry_run = self.confirm_sync()

            # Configure sync
            config = Config()
            config.sync.dry_run = dry_run

            # Perform sync
            sync_mgr = SyncManager(paths.source, paths.target, config)
            
            with self.create_progress() as progress:
                progress.update("[green]Syncing vault settings...")
                result = sync_mgr.sync_settings()

            self.display_sync_results(result, dry_run)

            if result.success and dry_run:
                # Offer to perform actual sync
                if self.confirm_sync(dry_run=False):
                    config.sync.dry_run = False
                    with self.create_progress() as progress:
                        progress.update("[green]Syncing vault settings...")
                        result = sync_mgr.sync_settings()
                        self.display_sync_results(result, dry_run=False)

            return result.success

        except Exception as e:
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