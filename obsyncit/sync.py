"""
Core sync functionality for Obsidian vaults.

This module handles the synchronization of settings, plugins, themes,
and snippets between different Obsidian vaults.
"""

import shutil
import json
import difflib
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from loguru import logger

from schemas import Config
from vault import VaultManager
from backup import BackupManager
from errors import (
    SyncError,
    VaultError,
    BackupError,
    ValidationError,
    handle_file_operation_error
)


class SyncPreview:
    """Represents a preview of sync operations."""
    
    def __init__(self):
        self.files_to_add: List[Path] = []
        self.files_to_update: List[Tuple[Path, List[str]]] = []
        self.files_to_remove: List[Path] = []
        self.dirs_to_add: List[Path] = []
        self.dirs_to_update: List[Path] = []
        self.dirs_to_remove: List[Path] = []

    def summarize(self) -> None:
        """Print a human-readable summary of the sync preview."""
        logger.info("=== Sync Preview ===")
        
        if self.files_to_add:
            logger.info("\nFiles to be added:")
            for f in self.files_to_add:
                logger.info(f"  + {f}")
                
        if self.files_to_update:
            logger.info("\nFiles to be updated:")
            for f, diff in self.files_to_update:
                logger.info(f"  ~ {f}")
                if diff:  # If we have a diff to show
                    logger.info("    Changes:")
                    for line in diff[:5]:  # Show first 5 lines of diff
                        logger.info(f"      {line}")
                    if len(diff) > 5:
                        logger.info(f"      ... and {len(diff) - 5} more lines")
                
        if self.files_to_remove:
            logger.info("\nFiles to be removed:")
            for f in self.files_to_remove:
                logger.info(f"  - {f}")
                
        if self.dirs_to_add:
            logger.info("\nDirectories to be added:")
            for d in self.dirs_to_add:
                logger.info(f"  + {d}/")
                
        if self.dirs_to_update:
            logger.info("\nDirectories to be updated:")
            for d in self.dirs_to_update:
                logger.info(f"  ~ {d}/")
                
        if self.dirs_to_remove:
            logger.info("\nDirectories to be removed:")
            for d in self.dirs_to_remove:
                logger.info(f"  - {d}/")

        if not any([self.files_to_add, self.files_to_update, self.files_to_remove,
                   self.dirs_to_add, self.dirs_to_update, self.dirs_to_remove]):
            logger.info("No changes to sync")


class SyncManager:
    """Handles synchronization between Obsidian vaults."""
    
    def __init__(self, source_vault: str | Path, target_vault: str | Path, config: Config, dry_run: bool = False):
        """
        Initialize the sync manager.
        
        Args:
            source_vault: Path to the source Obsidian vault
            target_vault: Path to the target Obsidian vault
            config: Configuration object
            dry_run: If True, only simulate the sync operation
            
        Raises:
            VaultError: If there are issues with vault paths
            ConfigError: If configuration is invalid
        """
        self.config = config
        self.dry_run = dry_run
        
        # Initialize vault managers
        self.source = VaultManager(source_vault, config.general.settings_dir)
        self.target = VaultManager(target_vault, config.general.settings_dir)
        
        # Initialize backup manager
        self.backup_manager = BackupManager(
            vault_path=self.target.vault_path,
            settings_dir=config.general.settings_dir,
            backup_count=config.general.backup_count,
            dry_run=dry_run
        )
        
        logger.debug(f"Initialized sync from {self.source.vault_path} to {self.target.vault_path}")

    def validate_vaults(self) -> bool:
        """
        Validate that both source and target vaults exist and are valid.
        
        Returns:
            bool: True if both vaults are valid
            
        Raises:
            VaultError: If validation fails for either vault
        """
        try:
            self.source.validate_vault()
            self.target.validate_vault()
            return True
        except VaultError:
            raise

    def list_backups(self) -> List[Path]:
        """
        List all available backups for the target vault.
        
        Returns:
            List[Path]: List of backup directory paths, sorted by creation time
            
        Raises:
            BackupError: If there are issues accessing backups
        """
        try:
            return self.backup_manager.list_backups()
        except Exception as e:
            raise BackupError(
                "Failed to list backups",
                self.target.vault_path,
                str(e)
            )

    def _generate_file_diff(self, source_file: Path, target_file: Path) -> List[str]:
        """
        Generate a human-readable diff between two files.
        
        Args:
            source_file: Path to source file
            target_file: Path to target file
            
        Returns:
            List[str]: List of diff lines
            
        Raises:
            SyncError: If there are issues generating the diff
        """
        try:
            if not source_file.exists():
                return []
                
            source_content = source_file.read_text().splitlines()
            target_content = target_file.read_text().splitlines() if target_file.exists() else []
            
            diff = list(difflib.unified_diff(
                target_content,
                source_content,
                fromfile=str(target_file),
                tofile=str(source_file),
                lineterm=''
            ))
            
            return diff
        except Exception as e:
            handle_file_operation_error(e, "generating diff for", source_file)
            raise SyncError(
                "Failed to generate file diff",
                source=source_file,
                target=target_file,
                details=str(e)
            )

    def _preview_sync(self, selected_items: Optional[List[str]] = None) -> SyncPreview:
        """
        Generate a preview of what would be synced.
        
        Args:
            selected_items: Optional list of specific settings to sync
            
        Returns:
            SyncPreview: Preview of sync operations
            
        Raises:
            SyncError: If there are issues generating the preview
        """
        preview = SyncPreview()
        
        try:
            # Determine what to sync
            files_to_sync = [f for f in self.config.sync.core_settings_files 
                          if not selected_items or f in selected_items]
            dirs_to_sync = [d for d in self.config.sync.settings_dirs 
                         if not selected_items or d in selected_items]

            # Check files
            for settings_file in files_to_sync:
                source_file = self.source.settings_path / settings_file
                target_file = self.target.settings_path / settings_file
                
                if source_file.exists():
                    if not target_file.exists():
                        preview.files_to_add.append(settings_file)
                    else:
                        diff = self._generate_file_diff(source_file, target_file)
                        if diff:
                            preview.files_to_update.append((settings_file, diff))
                elif target_file.exists():
                    preview.files_to_remove.append(settings_file)

            # Check directories
            for dir_name in dirs_to_sync:
                source_dir = self.source.settings_path / dir_name
                target_dir = self.target.settings_path / dir_name
                
                if source_dir.exists():
                    if not target_dir.exists():
                        preview.dirs_to_add.append(dir_name)
                    else:
                        # Check if directory contents differ
                        source_files = set(f.relative_to(source_dir) for f in source_dir.rglob("*"))
                        target_files = set(f.relative_to(target_dir) for f in target_dir.rglob("*"))
                        if source_files != target_files:
                            preview.dirs_to_update.append(dir_name)
                elif target_dir.exists():
                    preview.dirs_to_remove.append(dir_name)
                    
            return preview
        except Exception as e:
            raise SyncError(
                "Failed to generate sync preview",
                source=self.source.settings_path,
                target=self.target.settings_path,
                details=str(e)
            )

    def restore_backup(self, backup_path: Optional[Path] = None) -> bool:
        """
        Restore settings from a backup.
        
        Args:
            backup_path: Optional specific backup to restore. If None, uses most recent.
            
        Returns:
            bool: True if restore was successful
            
        Raises:
            VaultError: If there are issues with the vault
            BackupError: If there are issues with the backup
        """
        try:
            # Validate target vault before restore
            self.target.validate_vault()
            
            if self.dry_run:
                logger.info("=== Restore Preview ===")
                backup = backup_path or "latest backup"
                logger.info(f"Would restore from: {backup}")
                if self.target.settings_path.exists():
                    logger.info(f"Would create backup of current settings")
                    logger.info(f"Would replace contents of: {self.target.settings_path}")
                return True
            
            # Create a backup of current state before restore
            logger.info("Creating backup of current state before restore...")
            pre_restore_backup = self.backup_manager.create_backup()
            if pre_restore_backup is None:
                raise BackupError(
                    "Failed to create pre-restore backup",
                    details="Backup creation returned None"
                )
            logger.info(f"Pre-restore backup created at: {pre_restore_backup}")
            
            # Perform restore
            logger.info(f"Restoring from {'latest backup' if backup_path is None else backup_path}...")
            if not self.backup_manager.restore_backup(backup_path):
                raise BackupError(
                    "Failed to restore from backup",
                    backup_path
                )
            
            logger.success("Settings restore completed successfully!")
            return True
            
        except (VaultError, BackupError):
            raise
        except Exception as e:
            raise BackupError(
                "Error during restore operation",
                backup_path,
                str(e)
            )

    def sync_settings(self, selected_items: Optional[List[str]] = None) -> bool:
        """
        Synchronize settings from source to target vault.
        
        Args:
            selected_items: Optional list of specific settings to sync
            
        Returns:
            bool: True if sync was successful
            
        Raises:
            VaultError: If there are issues with the vaults
            BackupError: If there are issues with backups
            SyncError: If there are issues during sync
            ValidationError: If there are issues with file validation
        """
        try:
            self.validate_vaults()

            # In dry-run mode, show preview and return
            if self.dry_run:
                preview = self._preview_sync(selected_items)
                preview.summarize()
                return True

            # Create backup
            backup_path = self.backup_manager.create_backup()
            if backup_path is None:
                raise BackupError(
                    "Failed to create backup before sync",
                    details="Backup creation returned None"
                )

            # Create target .obsidian directory if it doesn't exist
            self.target.settings_path.mkdir(exist_ok=True)

            # Determine what to sync
            files_to_sync = [f for f in self.config.sync.core_settings_files 
                           if not selected_items or f in selected_items]
            dirs_to_sync = [d for d in self.config.sync.settings_dirs 
                          if not selected_items or d in selected_items]

            # Sync core settings files
            for settings_file in files_to_sync:
                source_file = self.source.settings_path / settings_file
                target_file = self.target.settings_path / settings_file
                
                if source_file.exists():
                    try:
                        if not self.source.validate_json_file(source_file):
                            continue
                        shutil.copy2(source_file, target_file)
                        logger.info(f"Synced settings file: {settings_file}")
                    except Exception as e:
                        handle_file_operation_error(e, "copying", source_file)
                        raise SyncError(
                            f"Failed to sync file: {settings_file}",
                            source=source_file,
                            target=target_file,
                            details=str(e)
                        )

            # Sync settings directories
            for dir_name in dirs_to_sync:
                source_dir = self.source.settings_path / dir_name
                target_dir = self.target.settings_path / dir_name
                
                if source_dir.exists():
                    try:
                        shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
                        logger.info(f"Synced directory: {dir_name}")
                    except Exception as e:
                        handle_file_operation_error(e, "copying directory", source_dir)
                        raise SyncError(
                            f"Failed to sync directory: {dir_name}",
                            source=source_dir,
                            target=target_dir,
                            details=str(e)
                        )

            # Cleanup old backups
            try:
                self.backup_manager.cleanup_old_backups()
            except Exception as e:
                logger.warning(f"Failed to clean up old backups: {str(e)}")

            logger.success("Settings sync completed successfully!")
            if backup_path:
                logger.info(f"Backup of original settings available at: {backup_path}")
            
            return True
            
        except (VaultError, BackupError, ValidationError, SyncError):
            raise
        except Exception as e:
            raise SyncError(
                "Unexpected error during sync",
                source=self.source.settings_path,
                target=self.target.settings_path,
                details=str(e)
            ) 