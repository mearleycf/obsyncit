#!/usr/bin/env python3

import logging
import sys
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

    def get_vault_paths(self):
        """Get source and target vault paths from user."""
        source_vault = Prompt.ask(
            "[green]Enter source vault path[/green]",
            default=str(Path.home() / "Documents/ObsidianVault")
        )
        target_vault = Prompt.ask(
            "[yellow]Enter target vault path[/yellow]",
            default=str(Path.home() / "Documents/ObsidianVault2")
        )
        return source_vault, target_vault

    def display_sync_preview(self, source: str, target: str):
        """Display a preview of the sync operation."""
        table = Table(title="Sync Operation Preview")
        table.add_column("Setting", style="cyan")
        table.add_column("Source", style="green")
        table.add_column("Target", style="yellow")

        source_path = Path(source)
        target_path = Path(target)

        table.add_row(
            "Source Vault",
            str(source_path),
            "✓" if source_path.exists() else "✗"
        )
        table.add_row(
            "Target Vault",
            str(target_path),
            "✓" if target_path.exists() else "✗"
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
