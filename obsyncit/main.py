#!/usr/bin/env python3

"""
Obsidian Settings Sync - Main entry point.

This module serves as the entry point for the Obsidian settings sync tool,
handling command-line arguments and orchestrating the sync process.
"""

import sys
import argparse
from pathlib import Path
import tomli
from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from schemas import Config
from logger import setup_logging
from sync import SyncManager
from errors import (
    ObsyncError,
    VaultError,
    ConfigError,
    BackupError,
    SyncError,
    ValidationError
)


def handle_error(error: Exception) -> int:
    """
    Handle different types of errors with appropriate messages and exit codes.
    
    Args:
        error: The exception to handle
        
    Returns:
        int: Exit code to use (0 for success, non-zero for errors)
    """
    if isinstance(error, VaultError):
        logger.error("Vault Error:")
        logger.error(error.full_message)
        return 2
    elif isinstance(error, ConfigError):
        logger.error("Configuration Error:")
        logger.error(error.full_message)
        return 3
    elif isinstance(error, ValidationError):
        logger.error("Validation Error:")
        logger.error(error.full_message)
        return 4
    elif isinstance(error, BackupError):
        logger.error("Backup Error:")
        logger.error(error.full_message)
        return 5
    elif isinstance(error, SyncError):
        logger.error("Sync Error:")
        logger.error(error.full_message)
        return 6
    elif isinstance(error, ObsyncError):
        logger.error("Error:")
        logger.error(error.full_message)
        return 1
    else:
        logger.error(f"Unexpected error: {str(error)}")
        logger.debug("", exc_info=True)  # Log full traceback at debug level
        return 1


def main() -> None:
    """Main entry point for the Obsidian settings sync tool."""
    parser = argparse.ArgumentParser(
        description="Sync Obsidian vault settings between different vaults"
    )
    parser.add_argument(
        "source_vault",
        help="Path to the source Obsidian vault"
    )
    parser.add_argument(
        "target_vault",
        help="Path to the target Obsidian vault"
    )
    parser.add_argument(
        "--config",
        default="config.toml",
        help="Path to the configuration file (default: config.toml)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the operation without making changes"
    )
    parser.add_argument(
        "--items",
        nargs="+",
        help="Specific settings files or directories to sync"
    )
    parser.add_argument(
        "--restore",
        nargs="?",
        const="latest",
        help="Restore settings from a backup. Use 'latest' or provide a backup path"
    )
    parser.add_argument(
        "--list-backups",
        action="store_true",
        help="List available backups for the target vault"
    )
    
    args = parser.parse_args()
    
    try:
        # Load and validate configuration
        config_path = Path(args.config)
        if not config_path.exists():
            raise ConfigError(
                "Configuration file not found",
                f"Path: {config_path}"
            )
            
        try:
            with open(config_path, 'rb') as f:
                config_data = tomli.load(f)
            config = Config.model_validate(config_data)
        except PydanticValidationError as e:
            errors = [f"{' -> '.join(str(loc) for loc in error['loc'])}: {error['msg']}"
                     for error in e.errors()]
            raise ConfigError(
                "Invalid configuration",
                "\n".join(errors)
            )
        except Exception as e:
            raise ConfigError(
                "Error reading configuration",
                str(e)
            )
            
        # Initialize logging
        setup_logging(config)
        
        # Initialize sync manager
        sync_manager = SyncManager(
            source_vault=args.source_vault,
            target_vault=args.target_vault,
            config=config,
            dry_run=args.dry_run
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
