#!/usr/bin/env python3

"""
Obsidian Settings Sync - Core functionality for syncing settings between Obsidian vaults.

This module provides the core functionality for synchronizing settings, plugins, themes,
and snippets between different Obsidian vaults. It includes features for backup creation,
JSON validation, and selective syncing of specific settings.
"""

import sys
import shutil
import json
import argparse
from pathlib import Path
from typing import List, Optional, Set
import tomli
from loguru import logger
from datetime import datetime
from jsonschema import validate, ValidationError
from pydantic import ValidationError as PydanticValidationError

from schemas import Config, SCHEMA_MAP
from backup import BackupManager


def setup_logging(config: Config) -> None:
    """
    Configure Loguru logging based on configuration.
    
    Args:
        config: Validated configuration object
    """
    log_config = config.logging
    log_dir = Path(log_config.log_dir)
    log_dir.mkdir(exist_ok=True)
    
    # Remove default handler
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stderr,
        format=log_config.format,
        level=log_config.level,
        colorize=True
    )
    
    # Add file handler
    logger.add(
        log_dir / "obsync_{time}.log",
        rotation=log_config.rotation,
        retention=log_config.retention,
        compression=log_config.compression,
        level="DEBUG",
        format=log_config.format
    )


class ObsidianSettingsSync:
    """Handles syncing of Obsidian settings between vaults."""
    
    def __init__(self, source_vault: str | Path, target_vault: str | Path, dry_run: bool = False, config_path: Path | str = Path("config.toml")):
        """
        Initialize the settings sync handler.
        
        Args:
            source_vault: Path to the source Obsidian vault
            target_vault: Path to the target Obsidian vault
            dry_run: If True, only simulate the sync operation
            config_path: Path to the TOML configuration file
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            PydanticValidationError: If config file has invalid structure
            tomli.TOMLDecodeError: If config file is invalid TOML
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        # Load and validate configuration
        try:
            with open(config_path, 'rb') as f:
                config_data = tomli.load(f)
            self.config = Config.model_validate(config_data)
        except PydanticValidationError as e:
            logger.error("Invalid configuration:")
            for error in e.errors():
                logger.error(f"  - {' -> '.join(str(loc) for loc in error['loc'])}: {error['msg']}")
            raise
            
        # Initialize logging
        setup_logging(self.config)
        
        # Set paths
        self.source_vault = Path(source_vault).expanduser().resolve()
        self.target_vault = Path(target_vault).expanduser().resolve()
        self.dry_run = dry_run
        
        # Initialize backup manager
        self.backup_manager = BackupManager(
            vault_path=self.target_vault,
            settings_dir=self.config.general.settings_dir,
            backup_count=self.config.general.backup_count,
            dry_run=self.dry_run
        )
        
        logger.debug(f"Initialized sync from {self.source_vault} to {self.target_vault}")

    def validate_paths(self) -> bool:
        """
        Validate that source and target paths exist and are Obsidian vaults.
        
        Returns:
            bool: True if paths are valid, False otherwise
        """
        try:
            if not self.source_vault.exists():
                logger.error(f"Source vault does not exist: {self.source_vault}")
                return False
            
            if not self.target_vault.exists():
                logger.error(f"Target vault does not exist: {self.target_vault}")
                return False
            
            source_settings = self.source_vault / self.config.general.settings_dir
            if not source_settings.exists():
                logger.error(f"Source vault has no .obsidian directory: {source_settings}")
                return False
                
            return True
        except PermissionError as e:
            logger.error(f"Permission denied accessing vault paths: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error validating paths: {str(e)}")
            return False

    def validate_json_file(self, file_path: Path) -> bool:
        """
        Validate that a file contains valid JSON and matches its schema.
        
        Args:
            file_path: Path to the JSON file to validate
            
        Returns:
            bool: True if JSON is valid and matches schema, False otherwise
        """
        try:
            if not file_path.exists():
                return True  # Skip validation for non-existent files
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Get schema for this file type
            file_name = file_path.name
            if file_name in SCHEMA_MAP:
                try:
                    validate(instance=data, schema=SCHEMA_MAP[file_name])
                except ValidationError as e:
                    logger.error(f"Schema validation failed for {file_path}:")
                    logger.error(f"  - {e.message}")
                    logger.debug(f"  - Path: {' -> '.join(str(p) for p in e.path)}")
                    logger.debug(f"  - Schema path: {' -> '.join(str(p) for p in e.schema_path)}")
                    return False
                    
            return True
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {str(e)}")
            return False
        except PermissionError as e:
            logger.error(f"Permission denied reading {file_path}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error reading {file_path}: {str(e)}")
            return False

    def sync_settings(self, selected_items: Optional[List[str]] = None) -> bool:
        """
        Synchronize settings from source to target vault.
        
        Args:
            selected_items: Optional list of specific settings to sync (files or directories)
            
        Returns:
            bool: True if sync was successful, False otherwise
        """
        try:
            if not self.validate_paths():
                return False

            # Create backup
            backup_path = self.backup_manager.create_backup()
            if backup_path is None:
                logger.error("Failed to create backup, aborting sync")
                return False
            
            source_settings = self.source_vault / self.config.general.settings_dir
            target_settings = self.target_vault / self.config.general.settings_dir

            # Create target .obsidian directory if it doesn't exist
            if not self.dry_run:
                target_settings.mkdir(exist_ok=True)

            # Determine what to sync
            files_to_sync = [f for f in self.config.sync.core_settings_files 
                           if not selected_items or f in selected_items]
            dirs_to_sync = [d for d in self.config.sync.settings_dirs 
                          if not selected_items or d in selected_items]

            # Sync core settings files
            for settings_file in files_to_sync:
                source_file = source_settings / settings_file
                target_file = target_settings / settings_file
                
                if source_file.exists():
                    if not self.validate_json_file(source_file):
                        continue
                        
                    if not self.dry_run:
                        shutil.copy2(source_file, target_file)
                    logger.info(f"Synced settings file: {settings_file}")

            # Sync settings directories
            for dir_name in dirs_to_sync:
                source_dir = source_settings / dir_name
                target_dir = target_settings / dir_name
                
                if source_dir.exists():
                    if not self.dry_run:
                        shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
                    logger.info(f"Synced directory: {dir_name}")

            # Cleanup old backups
            self.backup_manager.cleanup_old_backups()

            logger.success("Settings sync completed successfully!")
            if backup_path:
                logger.info(f"Backup of original settings available at: {backup_path}")
            
            return True
            
        except PermissionError as e:
            logger.error(f"Permission denied during sync: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error during sync: {str(e)}")
            return False


def main() -> None:
    """Entry point for the command line interface."""
    parser = argparse.ArgumentParser(description="Sync Obsidian settings between vaults")
    parser.add_argument("source_vault", help="Path to source vault")
    parser.add_argument("target_vault", help="Path to target vault")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be synced without making changes")
    parser.add_argument("--items", nargs="+", help="Specific settings to sync (files or directories)")
    parser.add_argument("--config", type=Path, default=Path("config.toml"), help="Path to configuration file")
    parser.add_argument("--restore-backup", type=Path, help="Restore from a specific backup")
    
    args = parser.parse_args()
    
    try:
        syncer = ObsidianSettingsSync(
            args.source_vault,
            args.target_vault,
            args.dry_run,
            args.config
        )
        
        if args.restore_backup:
            success = syncer.backup_manager.restore_backup(args.restore_backup)
        else:
            success = syncer.sync_settings(args.items)
            
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.exception("Fatal error during sync operation")
        sys.exit(1)


if __name__ == "__main__":
    main()
