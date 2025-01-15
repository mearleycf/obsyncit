#!/usr/bin/env python3

import logging
import sys
import os
from pathlib import Path
import json
from typing import Tuple

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from obsyncit import ObsidianSettingsSync
from obsyncit.schemas import Config
from obsyncit.errors import (
    ObsyncError,
    VaultError,
    ConfigError,
    ValidationError,
    BackupError,
    SyncError,
)


class ObsidianSyncTUI:
    def __init__(self):
        self.console = Console()

        # Configure Rich logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=self.console, rich_tracebacks=True)]
        )

    def display_header(self):
        """Display the application header."""
        self.console.print(Panel.fit(
            "[bold blue]Obsidian Settings Sync[/bold blue]\n"
            "[dim]Sync settings between Obsidian vaults[/dim]",
            border_style="blue"
        ))

    def validate_vault_path(self, path: str, is_target: bool = False) -> tuple[bool, str]:
        """
        Validate a vault path for basic issues.

        Args:
            path: The path to validate
            is_target: Whether this is a target vault (requires write access)

        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        try:
            path_obj = Path(path).resolve()
            
            # Check path syntax
            if not path_obj.parent.is_absolute():
                return False, "Path must be absolute"
            
            # Check parent directory exists
            if not path_obj.parent.exists():
                return False, f"Parent directory does not exist: {path_obj.parent}"
            
            # If path exists, check permissions
            if path_obj.exists():
                try:
                    if not os.access(path_obj, os.R_OK):
                        return False, "Path exists but is not readable"
                    if is_target and not os.access(path_obj, os.W_OK):
                        return False, "Target path exists but is not writable"
                except Exception as e:
                    return False, f"Permission check failed: {str(e)}"
                
            return True, ""
        except Exception as e:
            return False, f"Invalid path: {str(e)}"

    def get_vault_paths(self) -> Tuple[str, str]:
        """
        Get source and target vault paths from user.
        
        Validates paths for basic issues and allows retrying on invalid input.
        Does not validate vault structure - that's handled by the sync process.

        Returns:
            Tuple[str, str]: The source and target vault paths

        Raises:
            KeyboardInterrupt: If user cancels the input process
        """
        while True:
            source_vault = Prompt.ask(
                "[green]Enter source vault path[/green]",
                default=str(Path.home() / "Documents/ObsidianVault")
            )
            valid, error = self.validate_vault_path(source_vault)
            if not valid:
                self.console.print(f"[red]Invalid source path: {error}[/red]")
                if not Confirm.ask("[yellow]Try again?[/yellow]", default=True):
                    raise KeyboardInterrupt()
                continue
            break
        
        while True:
            target_vault = Prompt.ask(
                "[yellow]Enter target vault path[/yellow]",
                default=str(Path.home() / "Documents/ObsidianVault2")
            )
            valid, error = self.validate_vault_path(target_vault, is_target=True)
            if not valid:
                self.console.print(f"[red]Invalid target path: {error}[/red]")
                if not Confirm.ask("[yellow]Try again?[/yellow]", default=True):
                    raise KeyboardInterrupt()
                continue
            
            # Check if target is same as source
            if Path(target_vault).resolve() == Path(source_vault).resolve():
                self.console.print("[red]Target vault cannot be the same as source vault[/red]")
                if not Confirm.ask("[yellow]Try again?[/yellow]", default=True):
                    raise KeyboardInterrupt()
                continue
            break
        
        return source_vault, target_vault

    def display_sync_preview(self, source: str, target: str):
        """
        Display a preview of the sync operation.
        
        Shows the status of source and target paths, including:
        - Path existence
        - Basic permissions
        - Path resolution
        """
        table = Table(title="Sync Operation Preview")
        table.add_column("Setting", style="cyan")
        table.add_column("Source", style="green")
        table.add_column("Target", style="yellow")
        table.add_column("Status", style="blue")

        source_path = Path(source)
        target_path = Path(target)

        # Check source vault
        source_status = "✓" if source_path.exists() else "✗"
        if source_path.exists():
            if not os.access(source_path, os.R_OK):
                source_status = "⚠️ Not readable"

        # Check target vault
        target_status = "✓" if target_path.exists() else "New vault"
        if target_path.exists():
            if not os.access(target_path, os.W_OK):
                target_status = "⚠️ Not writable"

        table.add_row(
            "Source Vault",
            str(source_path.resolve()),
            "",
            source_status
        )
        table.add_row(
            "Target Vault",
            "",
            str(target_path.resolve()),
            target_status
        )

        self.console.print(table)

    def run(self):
        """Run the TUI application."""
        try:
            self.display_header()

            source_vault, target_vault = self.get_vault_paths()
            self.display_sync_preview(source_vault, target_vault)

            dry_run = Confirm.ask(
                "\n[yellow]Would you like to perform a dry run first?[/yellow]",
                default=True
            )

            if not Confirm.ask(
                "\n[bold red]Ready to proceed with sync?[/bold red]",
                default=False
            ):
                self.console.print("[yellow]Operation cancelled by user[/yellow]")
                return

            config = Config()  # Use default config for TUI
            config.sync.dry_run = dry_run  # Set dry run in config
            syncer = ObsidianSettingsSync(
                source_vault=source_vault,
                target_vault=target_vault,
                config=config
            )

            success = False  # Initialize success flag
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            )
            
            # Create progress bar but don't start it yet
            task = None
            with progress:
                task = progress.add_task(
                    description="[green]Syncing vault settings...",
                    total=None
                )
                success = syncer.sync_settings()

            if success:
                self.console.print("[green]✓ Sync completed successfully![/green]")
            else:
                self.console.print("[red]✗ Sync failed![/red]")

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Operation cancelled by user[/yellow]")
            sys.exit(0)
        except (VaultError, ConfigError, ValidationError, BackupError, SyncError) as e:
            # Handle specific ObsyncIt errors with appropriate messages
            error_type = type(e).__name__.replace("Error", " Error")
            self.console.print(f"[red]{error_type}:[/red]")
            self.console.print(f"[red]{e.full_message}[/red]")
            sys.exit(1)
        except ObsyncError as e:
            # Handle base ObsyncIt errors
            self.console.print(f"[red]Error: {e.full_message}[/red]")
            sys.exit(1)
        except json.JSONDecodeError as e:
            # Handle JSON parsing errors
            self.console.print(f"[red]Configuration Error: Invalid JSON format[/red]")
            self.console.print(f"[red]Details: {str(e)}[/red]")
            sys.exit(1)
        except PermissionError as e:
            # Handle permission-related errors
            self.console.print(f"[red]Permission Error: Unable to access required files or directories[/red]")
            self.console.print(f"[red]Details: {str(e)}[/red]")
            sys.exit(1)
        except FileNotFoundError as e:
            # Handle missing file errors
            self.console.print(f"[red]File Error: Required file or directory not found[/red]")
            self.console.print(f"[red]Details: {str(e)}[/red]")
            sys.exit(1)
        except OSError as e:
            # Handle other OS-related errors
            self.console.print(f"[red]System Error: Operation failed due to OS-level issue[/red]")
            self.console.print(f"[red]Details: {str(e)}[/red]")
            sys.exit(1)
        except Exception as e:
            # Handle truly unexpected errors with logging for debugging
            logging.exception("An unexpected error occurred")
            self.console.print(f"[red]Unexpected Error: {str(e)}[/red]")
            self.console.print("[yellow]This is an unexpected error. Please report this issue.[/yellow]")
            sys.exit(1)


def main():
    tui = ObsidianSyncTUI()
    tui.run()


if __name__ == "__main__":
    main()
