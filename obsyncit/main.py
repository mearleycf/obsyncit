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
        source_vault: Path to the source Obsidian vault
        target_vault: Path to the target Obsidian vault
        config: Path to the configuration file
        dry_run: Whether to simulate changes without making them
        items: Optional list of specific items to sync
        restore: Optional backup to restore from
        list_backups: Whether to list available backups
        list_vaults: Whether to list available Obsidian vaults
        search_path: Custom path to search for Obsidian vaults
        interactive: Whether to run in interactive mode with TUI
    """
    source_vault: Path
    target_vault: Path
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
  obsyncit --list-vaults ~/vault1 ~/vault2

  # Use custom search path
  obsyncit --search-path ~/vaults ~/vault1 ~/vault2''',
    )
    parser.add_argument(
        "source_vault",
        type=Path,
        help="Path to the source Obsidian vault",
    )
    parser.add_argument(
        "target_vault",
        type=Path,
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
    return Arguments(
        source_vault=parsed_args.source_vault,
        target_vault=parsed_args.target_vault,
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
    with a corresponding exit code based on the error type.

    Args:
        error: The exception to handle

    Returns:
        Never returns, always exits the program

    Example:
        >>> try:
        ...     raise VaultError("Invalid vault", "/path/to/vault")
        ... except Exception as e:
        ...     handle_error(e)
        Vault Error:
        Invalid vault
        Path: /path/to/vault
        # Exits with code 2
    """
    exit_code = ExitCode.GENERAL_ERROR

    if isinstance(error, VaultError):
        logger.error("Vault Error:")
        logger.error(error.full_message)
        exit_code = ExitCode.VAULT_ERROR

    elif isinstance(error, ConfigError):
        logger.error("Configuration Error:")
        logger.error(error.full_message)
        exit_code = ExitCode.CONFIG_ERROR

    elif isinstance(error, ValidationError):
        logger.error("Validation Error:")
        logger.error(error.full_message)
        exit_code = ExitCode.VALIDATION_ERROR

    elif isinstance(error, BackupError):
        logger.error("Backup Error:")
        logger.error(error.full_message)
        exit_code = ExitCode.BACKUP_ERROR

    elif isinstance(error, SyncError):
        logger.error("Sync Error:")
        logger.error(error.full_message)
        exit_code = ExitCode.SYNC_ERROR

    elif isinstance(error, ObsyncError):
        logger.error("Error:")
        logger.error(error.full_message)
        exit_code = ExitCode.GENERAL_ERROR

    else:
        logger.error(f"Unexpected error: {str(error)}")
        logger.debug("", exc_info=True)
        exit_code = ExitCode.GENERAL_ERROR

    sys.exit(exit_code.value)


def print_backups(backups: Sequence[BackupInfo]) -> None:
    """Display backup information in a formatted way.
    
    Args:
        backups: List of backup information objects
    """
    if not backups:
        logger.info("No backups found")
        return

    logger.info(f"Found {len(backups)} backup(s):")
    for idx, backup in enumerate(backups, 1):
        logger.info(f"\n{idx}. {backup}")


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