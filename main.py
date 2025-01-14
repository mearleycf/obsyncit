#!/usr/bin/env python3

"""
Obsidian Settings Sync - Main entry point.

This module serves as the entry point for the Obsidian settings sync tool,
handling command-line arguments and orchestrating the sync process.
"""

import argparse
from pathlib import Path
import tomli
from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from schemas import Config
from logger import setup_logging
from sync import SyncManager


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
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        try:
            with open(config_path, 'rb') as f:
                config_data = tomli.load(f)
            config = Config.model_validate(config_data)
        except PydanticValidationError as e:
            logger.error("Invalid configuration:")
            for error in e.errors():
                logger.error(f"  - {' -> '.join(str(loc) for loc in error['loc'])}: {error['msg']}")
            raise
            
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
        logger.error(f"Error: {str(e)}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
