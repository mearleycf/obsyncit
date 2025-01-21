#!/usr/bin/env python3

"""
Obsidian Settings Sync - Main entry point.

This module serves as the entry point for the Obsidian settings sync tool,
handling command-line arguments and orchestrating the sync process. It provides
a command-line interface for syncing settings between Obsidian vaults, managing
backups, and performing other related operations.

Usage examples:
    # Basic sync between two vaults
    $ obsyncit ~/vault1 ~/vault2

    # Dry run mode (simulate changes)
    $ obsyncit --dry-run ~/vault1 ~/vault2

    # Sync specific items only
    $ obsyncit --items appearance.json themes ~/vault1 ~/vault2

    # List available backups
    $ obsyncit --list-backups ~/vault1 ~/vault2

    # Restore from latest backup
    $ obsyncit --restore ~/vault1 ~/vault2

    # Use custom config file
    $ obsyncit --config my-config.toml ~/vault1 ~/vault2
"""

from __future__ import annotations

import sys
import argparse
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional, Sequence, NoReturn, Union

import tomli
from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from obsyncit.schemas import Config
from obsyncit.logger import setup_logging
from obsyncit.sync import SyncManager
from obsyncit.backup import BackupManager, BackupInfo
from obsyncit.vault_discovery import VaultDiscovery
from obsyncit.obsync_tui import ObsidianSyncTUI
from obsyncit.errors import (
    ObsyncError,
    VaultError,
    ConfigError,
    BackupError,
    SyncError,
    ValidationError,
)


class ExitCode(Enum):
    """Exit codes for different error conditions."""
    SUCCESS = 0
    GENERAL_ERROR = 1
    VAULT_ERROR = 2
    CONFIG_ERROR = 3
    VALIDATION_ERROR = 4
    BACKUP_ERROR = 5
    SYNC_ERROR = 6


@dataclass
class Arguments:
    """Command line arguments for the application.
    
    Attributes:
        source_vault: Optional path to the source Obsidian vault
        target_vault: Optional path to the target Obsidian vault
        config: Path to the configuration file
        dry_run: Whether to simulate changes without making them
        items: Optional list of specific items to sync
        restore: Optional backup to restore from
        list_backups: Whether to list available backups
        list_vaults: Whether to list available Obsidian vaults
        search_path: Custom path to search for Obsidian vaults
        interactive: Whether to run in interactive mode with TUI
    """
    source_vault: Optional[Path]
    target_vault: Optional[Path]
    config: Path
    dry_run: bool
    items: Optional[List[str]]
    restore: Optional[str]
    list_backups: bool
    list_vaults: bool
    search_path: Optional[Path]
    interactive: bool


def parse_args(args: Optional[Sequence[str]] = None) -> Arguments:
    """Parse command line arguments.
    
    Args:
        args: Command line arguments to parse. If None, uses sys.argv[1:]

    Returns:
        Parsed command line arguments

    Example:
        >>> args = parse_args(['~/vault1', '~/vault2', '--dry-run'])
        >>> print(args.dry_run)
        True
    """
    parser = argparse.ArgumentParser(
        description="Sync Obsidian vault settings between different vaults",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
examples:
  # Basic sync between two vaults
  obsyncit ~/vault1 ~/vault2

  # Dry run mode (simulate changes)
  obsyncit --dry-run ~/vault1 ~/vault2

  # Sync specific items only
  obsyncit --items appearance.json themes ~/vault1 ~/vault2

  # List available backups
  obsyncit --list-backups ~/vault1 ~/vault2

  # Restore from latest backup
  obsyncit --restore ~/vault1 ~/vault2

  # List available vaults
  obsyncit --list-vaults

  # Use custom search path
  obsyncit --list-vaults --search-path ~/vaults''',
    )
    parser.add_argument(
        "source_vault",
        type=Path,
        nargs="?",
        help="Path to the source Obsidian vault",
    )
    parser.add_argument(
        "target_vault",
        type=Path,
        nargs="?",
        help="Path to the target Obsidian vault",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default="config.toml",
        help="Path to the configuration file (default: config.toml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the operation without making changes",
    )
    parser.add_argument(
        "--items",
        nargs="+",
        help="Specific settings files or directories to sync",
    )
    parser.add_argument(
        "--restore",
        nargs="?",
        const="latest",
        help="Restore settings from a backup. Use 'latest' or provide a backup path",
    )
    parser.add_argument(
        "--list-backups",
        action="store_true",
        help="List available backups for the target vault",
    )
    parser.add_argument(
        "--list-vaults",
        action="store_true",
        help="List available Obsidian vaults",
    )
    parser.add_argument(
        "--search-path",
        type=Path,
        help="Custom path to search for Obsidian vaults",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode with TUI",
    )

    parsed_args = parser.parse_args(args)

    # Validate arguments
    if not (parsed_args.list_vaults or parsed_args.interactive):
        if not parsed_args.source_vault or not parsed_args.target_vault:
            parser.error("source_vault and target_vault are required unless using --list-vaults or --interactive")

    return Arguments(
        source_vault=parsed_args.source_vault if hasattr(parsed_args, 'source_vault') else None,
        target_vault=parsed_args.target_vault if hasattr(parsed_args, 'target_vault') else None,
        config=parsed_args.config,
        dry_run=parsed_args.dry_run,
        items=parsed_args.items,
        restore=parsed_args.restore,
        list_backups=parsed_args.list_backups,
        list_vaults=parsed_args.list_vaults,
        search_path=parsed_args.search_path,
        interactive=parsed_args.interactive,
    )


def load_config(config_path: Path) -> Config:
    """Load and validate configuration from a TOML file.
    
    Args:
        config_path: Path to the configuration file

    Returns:
        Validated configuration object

    Raises:
        ConfigError: If the file doesn't exist or contains invalid configuration
    """
    if not config_path.exists():
        raise ConfigError(
            "Configuration file not found",
            f"Path: {config_path}",
        )

    try:
        with open(config_path, "rb") as f:
            config_data = tomli.load(f)
        return Config.model_validate(config_data)
    except PydanticValidationError as e:
        errors = [
            f"{' -> '.join(str(loc) for loc in error['loc'])}: {error['msg']}"
            for error in e.errors()
        ]
        raise ConfigError("Invalid configuration", "\n".join(errors)) from e
    except Exception as e:
        raise ConfigError("Error reading configuration", str(e)) from e


def handle_error(error: Exception) -> NoReturn:
    """Handle different types of errors with appropriate messages and exit codes.
    
    This function logs the error with an appropriate message and exits the program
    with a corresponding exit code based on the error type. It ensures consistent
    error handling across the application.

    Args:
        error: The exception to handle. Supported types:
            - ObsyncError and subclasses (VaultError, ConfigError, etc.)
            - Other exceptions (treated as general errors)

    Returns:
        Never returns, always exits the program with an appropriate code

    Example:
        >>> try:
        ...     sync_mgr.sync_settings()
        ... except Exception as e:
        ...     handle_error(e)  # Exits with appropriate code
    """
    if isinstance(error, VaultError):
        logger.error(f"Invalid vault: {error.vault_path}")
        logger.debug(f"Details: {error.message}")
        sys.exit(ExitCode.VAULT_ERROR.value)
    elif isinstance(error, ConfigError):
        logger.error(f"Configuration error: {error.message}")
        if error.details:
            logger.debug(f"Details:\n{error.details}")
        sys.exit(ExitCode.CONFIG_ERROR.value)
    elif isinstance(error, ValidationError):
        logger.error(f"Validation error: {error.message}")
        if error.details:
            logger.debug(f"Details:\n{error.details}")
        sys.exit(ExitCode.VALIDATION_ERROR.value)
    elif isinstance(error, BackupError):
        logger.error(f"Backup error: {error.message}")
        if error.details:
            logger.debug(f"Details:\n{error.details}")
        sys.exit(ExitCode.BACKUP_ERROR.value)
    elif isinstance(error, SyncError):
        logger.error(f"Sync error: {error.message}")
        if error.errors:
            logger.debug("Failed items:")
            for item, err in error.errors.items():
                logger.debug(f"  {item}: {err}")
        sys.exit(ExitCode.SYNC_ERROR.value)
    elif isinstance(error, ObsyncError):
        logger.error(str(error))
        sys.exit(ExitCode.GENERAL_ERROR.value)
    else:
        logger.exception("Unexpected error")
        sys.exit(ExitCode.GENERAL_ERROR.value)


def print_backups(backups: Sequence[BackupInfo]) -> None:
    """Print a formatted list of available backups.
    
    This function displays backup information in a user-friendly format,
    including timestamp, size, and validation status for each backup.
    If no backups are available, it prints an appropriate message.

    Args:
        backups: Sequence of BackupInfo objects to display

    Example:
        >>> mgr = BackupManager("vault_path")
        >>> backups = mgr.list_backups()
        >>> print_backups(backups)
        Available backups:
          2024-01-19 14:30:23 - 5.2MB (verified)
          2024-01-18 09:15:07 - 4.8MB (verified)
    """
    if not backups:
        print("No backups available")
        return

    print("\nAvailable backups:")
    for backup in backups:
        status = "(verified)" if backup.is_verified else ""
        print(f"  {backup.timestamp} - {backup.size_mb:.1f}MB {status}")


def main(args: Optional[Sequence[str]] = None) -> None:
    """Main entry point for the Obsidian settings sync tool.
    
    This function orchestrates the entire sync process:
    1. Parses command line arguments
    2. Loads and validates configuration
    3. Sets up logging
    4. Performs the requested operation (sync, backup, restore)

    Args:
        args: Optional command line arguments. If None, uses sys.argv[1:]

    Raises:
        SystemExit: Always exits with an appropriate status code
    """
    try:
        # Parse arguments
        cli_args = parse_args(args)

        # Load and validate configuration
        config = load_config(cli_args.config)

        # Initialize logging
        setup_logging(config)

        # Handle vault discovery
        if cli_args.list_vaults or cli_args.search_path:
            discovery = VaultDiscovery(cli_args.search_path)
            vaults = discovery.find_vaults()
            logger.info(f"Found {len(vaults)} vaults:")
            for vault in vaults:
                logger.info(f"  - {vault}")
            sys.exit(ExitCode.SUCCESS.value)

        # Handle interactive mode
        if cli_args.interactive:
            tui = ObsidianSyncTUI(
                source_vault=cli_args.source_vault,
                target_vault=cli_args.target_vault,
                config=config,
            )
            if not tui.run():
                sys.exit(ExitCode.GENERAL_ERROR.value)
            sys.exit(ExitCode.SUCCESS.value)

        # Update config with command line overrides
        config.sync.dry_run = cli_args.dry_run

        # Initialize sync manager
        sync_manager = SyncManager(
            source_vault=cli_args.source_vault,
            target_vault=cli_args.target_vault,
            config=config,
        )

        # Handle different operations
        if cli_args.list_backups:
            backups = sync_manager.list_backups()
            print_backups(backups)
            sys.exit(ExitCode.SUCCESS.value)

        if cli_args.restore:
            backup_path = (
                None if cli_args.restore == "latest"
                else Path(cli_args.restore)
            )
            if not sync_manager.restore_backup(backup_path):
                raise RuntimeError("Restore operation failed")
            sys.exit(ExitCode.SUCCESS.value)

        # Perform sync
        result = sync_manager.sync_settings(cli_args.items)
        if not result.success:
            message = [str(result)]
            if result.errors:
                message.extend([
                    "\nErrors:",
                    *(f"  - {item}: {error}" for item, error in result.errors.items())
                ])
            raise RuntimeError("\n".join(message))

        sys.exit(ExitCode.SUCCESS.value)

    except Exception as e:
        handle_error(e)


if __name__ == "__main__":
    main()
