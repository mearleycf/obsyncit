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
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set
import tomli
from loguru import logger
from datetime import datetime

@dataclass
class SyncConfig:
    """Configuration for the sync operation."""
    source_vault: Path
    target_vault: Path
    dry_run: bool
    settings_dir: str
    backup_count: int
    core_settings_files: Set[str]
    settings_dirs: Set[str]

    @classmethod
    def from_toml(cls, config_path: Path, source_vault: Path, target_vault: Path, dry_run: bool) -> 'SyncConfig':
        """
        Create a configuration instance from a TOML file.
        
        Args:
            config_path: Path to the TOML configuration file
            source_vault: Path to the source vault
            target_vault: Path to the target vault
            dry_run: Whether to perform a dry run
            
        Returns:
            SyncConfig: Configuration instance
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            tomli.TOMLDecodeError: If config file is invalid
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        with open(config_path, 'rb') as f:
            config = tomli.load(f)
            
        return cls(
            source_vault=source_vault,
            target_vault=target_vault,
            dry_run=dry_run,
            settings_dir=config['general']['settings_dir'],
            backup_count=config['general']['backup_count'],
            core_settings_files=frozenset(config['sync']['core_settings_files']),
            settings_dirs=frozenset(config['sync']['settings_dirs'])
        )

def setup_logging(config_path: Path) -> None:
    """
    Configure Loguru logging based on TOML configuration.
    
    Args:
        config_path: Path to the TOML configuration file
    """
    with open(config_path, 'rb') as f:
        config = tomli.load(f)
    
    log_config = config['logging']
    log_dir = Path(log_config['log_dir'])
    log_dir.mkdir(exist_ok=True)
    
    # Remove default handler
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stderr,
        format=log_config['format'],
        level=log_config['level'],
        colorize=True
    )
    
    # Add file handler
    logger.add(
        log_dir / "obsync_{time}.log",
        rotation=log_config['rotation'],
        retention=log_config['retention'],
        compression=log_config['compression'],
        level="DEBUG",
        format=log_config['format']
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
        """
        config_path = Path(config_path)
        setup_logging(config_path)
        
        self.config = SyncConfig.from_toml(
            config_path,
            Path(source_vault).expanduser().resolve(),
            Path(target_vault).expanduser().resolve(),
            dry_run
        )
        
        logger.debug(f"Initialized sync from {self.config.source_vault} to {self.config.target_vault}")

    def validate_paths(self) -> bool:
        """
        Validate that source and target paths exist and are Obsidian vaults.
        
        Returns:
            bool: True if paths are valid, False otherwise
        """
        try:
            if not self.config.source_vault.exists():
                logger.error(f"Source vault does not exist: {self.config.source_vault}")
                return False
            
            if not self.config.target_vault.exists():
                logger.error(f"Target vault does not exist: {self.config.target_vault}")
                return False
            
            source_settings = self.config.source_vault / self.config.settings_dir
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
        Validate that a file contains valid JSON.
        
        Args:
            file_path: Path to the JSON file to validate
            
        Returns:
            bool: True if JSON is valid or file doesn't exist, False otherwise
        """
        try:
            if not file_path.exists():
                return True  # Skip validation for non-existent files
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
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

    def backup_target_settings(self) -> Optional[Path]:
        """
        Create a backup of target vault settings.
        
        Returns:
            Optional[Path]: Path to backup directory if successful, None otherwise
        """
        try:
            target_settings = self.config.target_vault / self.config.settings_dir
            if target_settings.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_dir = target_settings.parent / f"{self.config.settings_dir}_backup_{timestamp}"
                if not self.config.dry_run:
                    shutil.copytree(target_settings, backup_dir, dirs_exist_ok=True)
                logger.info(f"Created backup of target settings at: {backup_dir}")
                return backup_dir
        except PermissionError as e:
            logger.error(f"Permission denied creating backup: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
        return None

    def cleanup_old_backups(self) -> None:
        """Clean up old backups, keeping only the specified number of latest backups."""
        try:
            backup_pattern = f"{self.config.settings_dir}_backup_*"
            backups = sorted(self.config.target_vault.glob(backup_pattern))
            if len(backups) > self.config.backup_count:
                for backup in backups[:-self.config.backup_count]:
                    if not self.config.dry_run:
                        shutil.rmtree(backup)
                    logger.info(f"Removed old backup: {backup}")
        except PermissionError as e:
            logger.error(f"Permission denied cleaning up backups: {str(e)}")
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {str(e)}")

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
            backup_path = self.backup_target_settings()
            
            source_settings = self.config.source_vault / self.config.settings_dir
            target_settings = self.config.target_vault / self.config.settings_dir

            # Create target .obsidian directory if it doesn't exist
            if not self.config.dry_run:
                target_settings.mkdir(exist_ok=True)

            # Determine what to sync
            files_to_sync = [f for f in self.config.core_settings_files 
                           if not selected_items or f in selected_items]
            dirs_to_sync = [d for d in self.config.settings_dirs 
                          if not selected_items or d in selected_items]

            # Sync core settings files
            for settings_file in files_to_sync:
                source_file = source_settings / settings_file
                target_file = target_settings / settings_file
                
                if source_file.exists():
                    if not self.validate_json_file(source_file):
                        continue
                        
                    if not self.config.dry_run:
                        shutil.copy2(source_file, target_file)
                    logger.info(f"Synced settings file: {settings_file}")

            # Sync settings directories
            for dir_name in dirs_to_sync:
                source_dir = source_settings / dir_name
                target_dir = target_settings / dir_name
                
                if source_dir.exists():
                    if not self.config.dry_run:
                        shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
                    logger.info(f"Synced directory: {dir_name}")

            # Cleanup old backups
            self.cleanup_old_backups()

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
    
    args = parser.parse_args()
    
    try:
        syncer = ObsidianSettingsSync(
            args.source_vault,
            args.target_vault,
            args.dry_run,
            args.config
        )
        success = syncer.sync_settings(args.items)
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.exception("Fatal error during sync operation")
        sys.exit(1)

if __name__ == "__main__":
    main()
