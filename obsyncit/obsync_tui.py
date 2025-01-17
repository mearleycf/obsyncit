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
from typing import Optional, List, Dict

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


class SyncProgress:
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

    def __enter__(self) -> "SyncProgress":
        """Start progress context."""
        self.progress.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Clean up progress display."""
        self.progress.stop()

    def start(self, description: str) -> None:
        """Start a new progress task.
        
        Args:
            description: Task description to display
        """
        self.task_id = self.progress.add_task(description, total=None)


class ObsidianSyncTUI:
    """Text User Interface for Obsidian Settings Sync."""

    def __init__(self, search_path: Optional[Path] = None):
        """Initialize the TUI.
        
        Args:
            search_path: Optional path to search for vaults. Defaults to current directory.
        """
        self.console = Console(theme=Theme({
            "info": Style.INFO.value,
            "warning": Style.WARNING.value,
            "error": Style.ERROR.value,
            "success": Style.SUCCESS.value,
        }))
        self.vault_discovery = VaultDiscovery(search_path or Path.cwd())
        self.config = Config()

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
        """
        with SyncProgress(self.console) as progress:
            progress.start("[green]Searching for vaults...")
            available_vaults = self.vault_discovery.find_vaults()
            progress.progress.update(progress.task_id, completed=True)

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
        source_vault = available_vaults[source_idx]

        # Get target vault
        remaining_vaults = [v for i, v in enumerate(available_vaults) if i != source_idx]
        target_idx = int(Prompt.ask(
            f"[{Style.INFO.value}]Select target vault (1-{len(remaining_vaults)})[/]"
        )) - 1
        target_vault = remaining_vaults[target_idx]

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
            default=False,
        )

        if not proceed:
            self.console.print(f"[{Style.WARNING.value}]Operation cancelled by user[/]")
            return False

        return dry_run_confirmed

    def run(self) -> None:
        """Run the TUI application."""
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
            
            with SyncProgress(self.console) as progress:
                progress.start("[green]Syncing vault settings...")
                result = sync_mgr.sync_settings()

            if result.success:
                self.console.print(
                    f"[{Style.SUCCESS.value}]"
                    f"{Status.SUCCESS.value} "
                    f"{'Dry run completed' if dry_run else 'Sync completed'} "
                    f"successfully![/]"
                )
                if dry_run:
                    # Offer to perform actual sync
                    if self.confirm_sync(dry_run=False):
                        config.sync.dry_run = False
                        with SyncProgress(self.console) as progress:
                            progress.start("[green]Syncing vault settings...")
                            result = sync_mgr.sync_settings()
                            if result.success:
                                self.console.print(
                                    f"[{Style.SUCCESS.value}]"
                                    f"{Status.SUCCESS.value} "
                                    f"Sync completed successfully![/]"
                                )
                            else:
                                self.console.print(
                                    f"[{Style.ERROR.value}]"
                                    f"{Status.FAILURE.value} "
                                    f"Sync failed: {result.errors}[/]"
                                )
            else:
                self.console.print(
                    f"[{Style.ERROR.value}]"
                    f"{Status.FAILURE.value} "
                    f"{'Dry run' if dry_run else 'Sync'} failed: {result.errors}[/]"
                )

        except Exception as e:
            self.console.print(f"[{Style.ERROR.value}]Error: {str(e)}[/]")
            if isinstance(e, ObsyncError):
                self.console.print(f"[{Style.DIM.value}]Details: {e.details}[/]")
            self.console.print_exception()
            sys.exit(1)


def main() -> None:
    """Entry point for the TUI application."""
    setup_logging(Config())
    tui = ObsidianSyncTUI()
    tui.run()


if __name__ == "__main__":
    main()