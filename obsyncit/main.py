#!/usr/bin/env python3

"""
Obsidian Settings Sync - Main entry point.

This module serves as the entry point for the Obsidian settings sync tool,
handling command-line arguments and orchestrating the sync process.

The module provides the following functionality:
- Command-line argument parsing
- Configuration file loading and validation
- Error handling with appropriate exit codes
- Logging setup
- Sync operation orchestration
- Backup management

Example usage:
    $ python -m obsyncit.main /path/to/source /path/to/target
    $ python -m obsyncit.main --dry-run /source /target
    $ python -m obsyncit.main --items themes plugins /source /target
    $ python -m obsyncit.main --restore latest /target
    $ python -m obsyncit.main --list-backups /target

Exit codes:
    0: Success
    1: General error
    2: Vault error (e.g., invalid vault path)
    3: Configuration error
    4: Validation error
    5: Backup error
    6: Sync error
"""

import sys
import argparse
from pathlib import Path
import tomli
from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from obsyncit.schemas import Config
from obsyncit.logger import setup_logging
from obsyncit.sync import SyncManager
from obsyncit.errors import (
    ObsyncError,
    VaultError,
    ConfigError,
    BackupError,
    SyncError,
    ValidationError,
)


def handle_error(error: Exception) -> int:
    """
    Handle different types of errors with appropriate messages and exit codes.

    This function processes various types of exceptions that can occur during
    the sync operation and returns appropriate exit codes. It also logs
    error messages with different levels of detail based on the error type.

    Error handling hierarchy:
    1. Specific errors (VaultError, ConfigError, etc.)
    2. Base ObsyncError
    3. Unexpected errors

    Args:
        error: The exception to handle. Can be any Exception type, but
              special handling is provided for ObsyncError and its subclasses.

    Returns:
        int: Exit code to use (0 for success, non-zero for errors)
            - 1: General/unexpected error
            - 2: Vault error
            - 3: Configuration error
            - 4: Validation error
            - 5: Backup error
            - 6: Sync error

    Example:
        try:
            sync_manager.sync_settings()
        except Exception as e:
            sys.exit(handle_error(e))
    """
    if isinstance(error, VaultError):
        logger.error("Vault Error:")
        logger.error(error.full_message)
        return 2

    if isinstance(error, ConfigError):
        logger.error("Configuration Error:")
        logger.error(error.full_message)
        return 3

    if isinstance(error, ValidationError):
        logger.error("Validation Error:")
        logger.error(error.full_message)
        return 4

    if isinstance(error, BackupError):
        logger.error("Backup Error:")
        logger.error(error.full_message)
        return 5

    if isinstance(error, SyncError):
        logger.error("Sync Error:")
        logger.error(error.full_message)
        return 6

    if isinstance(error, ObsyncError):
        logger.error("Error:")
        logger.error(error.full_message)
        return 1

    logger.error(f"Unexpected error: {str(error)}")
    logger.debug("", exc_info=True)  # Log full traceback at debug level
    return 1


def main():
    """
    Main entry point for the Obsidian Settings Sync tool.

    This function handles the complete workflow of the sync operation:
    1. Parse command-line arguments
    2. Load and validate configuration
    3. Set up logging
    4. Initialize sync manager
    5. Execute requested operation (sync/restore/list backups)
    6. Handle any errors that occur

    Command-line arguments:
        source_vault: Path to the source Obsidian vault
        target_vault: Path to the target Obsidian vault
        --config: Path to configuration file (default: config.toml)
        --dry-run: Simulate the operation without making changes
        --items: Specific settings files or directories to sync
        --restore: Restore settings from a backup
        --list-backups: List available backups for the target vault

    Returns:
        None. The function will call sys.exit() with an appropriate
        exit code based on the operation's success or failure.

    Example:
        # Basic sync
        $ obsyncit /source /target

        # Dry run with specific items
        $ obsyncit --dry-run --items themes plugins /source /target

        # Restore from latest backup
        $ obsyncit --restore latest /target
    """
    parser = argparse.ArgumentParser(
        description="Sync Obsidian vault settings between different vaults"
    )
    parser.add_argument("source_vault", help="Path to the source Obsidian vault")
    parser.add_argument("target_vault", help="Path to the target Obsidian vault")
    parser.add_argument(
        "--config",
        default="config.toml",
        help="Path to the configuration file (default: config.toml)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate the operation without making changes"
    )
    parser.add_argument("--items", nargs="+", help="Specific settings files or directories to sync")
    parser.add_argument(
        "--restore",
        nargs="?",
        const="latest",
        help="Restore settings from a backup. Use 'latest' or provide a backup path",
    )
    parser.add_argument(
        "--list-backups", action="store_true", help="List available backups for the target vault"
    )

    args = parser.parse_args()

    try:
        # Load and validate configuration
        config_path = Path(args.config)
        if not config_path.exists():
            raise ConfigError("Configuration file not found", f"Path: {config_path}")

        try:
            with open(config_path, "rb") as f:
                config_data = tomli.load(f)
            config = Config.model_validate(config_data)
        except PydanticValidationError as e:
            errors = [
                f"{' -> '.join(str(loc) for loc in error['loc'])}: {error['msg']}"
                for error in e.errors()
            ]
            raise ConfigError("Invalid configuration", "\n".join(errors)) from e
        except Exception as e:
            raise ConfigError("Error reading configuration", str(e)) from e

        # Initialize logging
        setup_logging(config)

        # Initialize sync manager
        sync_manager = SyncManager(
            source_vault=args.source_vault,
            target_vault=args.target_vault,
            config=config,
            dry_run=args.dry_run,
        )

        if args.list_backups:
            # List available backups
            backups = sync_manager.list_backups()
            if not backups:
                logger.info("No backups found")
            else:
                logger.info("Available backups:")
                for backup in backups:
                    logger.info(f"  - {backup}")
            return

        if args.restore:
            # Handle restore operation
            backup_path = None if args.restore == "latest" else Path(args.restore)
            if not sync_manager.restore_backup(backup_path):
                raise RuntimeError("Restore operation failed")
            return

        # Perform sync
        if not sync_manager.sync_settings(args.items):
            raise RuntimeError("Sync operation failed")

    except Exception as e:
        sys.exit(handle_error(e))


if __name__ == "__main__":
    main()
