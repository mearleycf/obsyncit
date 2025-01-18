"""
Obsidian Settings Sync - Text User Interface.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
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
        """Update progress status."""
        raise NotImplementedError


class SyncProgress(ProgressInterface):
    """Manages progress indication during sync operations."""

    def __init__(self, console: Console):
        self.console = console
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        )
        self.task_id: Optional[TaskID] = None

    def start(self) -> None:
        self.progress.start()

    def stop(self) -> None:
        self.progress.stop()

    def update(self, description: str, completed: bool = False) -> None:
        if self.task_id is None:
            self.task_id = self.progress.add_task(description, total=None)
        self.progress.update(self.task_id, description=description, completed=completed)


class MockProgress(ProgressInterface):
    """Mock progress indicator for testing."""

    def __init__(self):
        self.started = False
        self.stopped = False
        self.updates: List[tuple[str, bool]] = []

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def update(self, description: str, completed: bool = False) -> None:
        self.updates.append((description, completed))


class ObsidianSyncTUI:
    """Text User Interface for Obsidian Settings Sync."""

    def __init__(
        self,
        search_path: Optional[Path] = None,
        progress_factory: Optional[type[ProgressInterface]] = None
    ):
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
        if self._progress_factory == SyncProgress:
            return self._progress_factory(self.console)
        return self._progress_factory()

    def display_header(self) -> None:
        self.console.print(Panel(
            "[bold]Obsidian Settings Sync[/bold]\n"
            "Synchronize settings between Obsidian vaults",
            style=Style.INFO.value,
        ))

    def get_vault_paths(self) -> VaultPaths:
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
        
        Args:
            dry_run: Whether to suggest a dry run first

        Returns:
            Tuple of (should_proceed, is_dry_run)
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
        """Run the TUI application."""
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
            sync_items = ["appearance.json", "themes", "snippets"]  # Default items to sync
            
            with self.create_progress() as progress:
                progress.update("[green]Syncing vault settings...")
                logger.debug("Calling sync_settings()")
                result = sync_mgr.sync_settings(sync_items)

            self.display_sync_results(result, is_dry_run)

            if result.success and is_dry_run:
                logger.debug("Dry run succeeded, offering actual sync")
                should_proceed, _ = self.confirm_sync(dry_run=False)
                if should_proceed:
                    self.config.sync.dry_run = False
                    with self.create_progress() as progress:
                        progress.update("[green]Syncing vault settings...")
                        logger.debug("Calling sync_settings() for actual sync")
                        result = sync_mgr.sync_settings(sync_items)
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