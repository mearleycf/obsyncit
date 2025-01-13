"""
Backup management functionality for Obsidian settings.

This module provides backup creation, verification, and cleanup functionality
for Obsidian vault settings. It supports different backup strategies and
rotation policies to ensure safe settings synchronization.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from loguru import logger


class BackupManager:
    """Manages backups of Obsidian settings."""

    def __init__(self, vault_path: Path, settings_dir: str, backup_count: int, dry_run: bool = False):
        """
        Initialize the backup manager.
        
        Args:
            vault_path: Path to the Obsidian vault
            settings_dir: Name of the settings directory (e.g., '.obsidian')
            backup_count: Number of backups to retain
            dry_run: If True, only simulate operations
        """
        self.vault_path = Path(vault_path).resolve()
        self.settings_dir = settings_dir
        self.backup_count = backup_count
        self.dry_run = dry_run
        self.settings_path = self.vault_path / self.settings_dir

    def _generate_backup_name(self, timestamp: Optional[datetime] = None) -> str:
        """
        Generate a backup directory name.
        
        Args:
            timestamp: Optional timestamp to use, defaults to current time
            
        Returns:
            str: Name of the backup directory
        """
        if timestamp is None:
            timestamp = datetime.now()
        return f"{self.settings_dir}_backup_{timestamp.strftime('%Y%m%d_%H%M%S')}"

    def _verify_backup(self, backup_path: Path) -> bool:
        """
        Verify that a backup was created successfully.
        
        Args:
            backup_path: Path to the backup directory
            
        Returns:
            bool: True if backup is valid, False otherwise
        """
        try:
            if not backup_path.exists():
                logger.error(f"Backup directory does not exist: {backup_path}")
                return False

            # Check if backup has same structure as original
            for original_item in self.settings_path.rglob("*"):
                relative_path = original_item.relative_to(self.settings_path)
                backup_item = backup_path / relative_path
                
                if original_item.is_file() and not backup_item.is_file():
                    logger.error(f"Missing file in backup: {relative_path}")
                    return False
                elif original_item.is_dir() and not backup_item.is_dir():
                    logger.error(f"Missing directory in backup: {relative_path}")
                    return False

            return True
        except Exception as e:
            logger.error(f"Error verifying backup: {str(e)}")
            return False

    def list_backups(self) -> List[Path]:
        """
        List all existing backups, sorted by creation time.
        
        Returns:
            List[Path]: List of backup directory paths
        """
        backup_pattern = f"{self.settings_dir}_backup_*"
        return sorted(self.vault_path.glob(backup_pattern))

    def create_backup(self) -> Optional[Path]:
        """
        Create a new backup of the settings directory.
        
        Returns:
            Optional[Path]: Path to the created backup directory if successful, None otherwise
        """
        try:
            if not self.settings_path.exists():
                logger.error(f"Settings directory does not exist: {self.settings_path}")
                return None

            backup_dir = self.vault_path / self._generate_backup_name()
            
            if not self.dry_run:
                shutil.copytree(self.settings_path, backup_dir, dirs_exist_ok=True)
                if not self._verify_backup(backup_dir):
                    logger.error("Backup verification failed")
                    try:
                        shutil.rmtree(backup_dir)
                    except Exception as e:
                        logger.error(f"Error cleaning up failed backup: {str(e)}")
                    return None
                    
            logger.info(f"Created backup of settings at: {backup_dir}")
            return backup_dir
            
        except PermissionError as e:
            logger.error(f"Permission denied creating backup: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
        return None

    def cleanup_old_backups(self) -> None:
        """Clean up old backups, keeping only the specified number of most recent backups."""
        try:
            backups = self.list_backups()
            if len(backups) > self.backup_count:
                for backup in backups[:-self.backup_count]:
                    if not self.dry_run:
                        shutil.rmtree(backup)
                    logger.info(f"Removed old backup: {backup}")
        except PermissionError as e:
            logger.error(f"Permission denied cleaning up backups: {str(e)}")
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {str(e)}")

    def restore_backup(self, backup_path: Optional[Path] = None) -> bool:
        """
        Restore settings from a backup.
        
        Args:
            backup_path: Optional specific backup to restore. If None, uses most recent.
            
        Returns:
            bool: True if restore was successful, False otherwise
        """
        try:
            if backup_path is None:
                backups = self.list_backups()
                if not backups:
                    logger.error("No backups found to restore")
                    return False
                backup_path = backups[-1]

            if not backup_path.exists():
                logger.error(f"Backup does not exist: {backup_path}")
                return False

            if not self._verify_backup(backup_path):
                logger.error("Backup verification failed")
                return False

            if not self.dry_run:
                if self.settings_path.exists():
                    shutil.rmtree(self.settings_path)
                shutil.copytree(backup_path, self.settings_path, dirs_exist_ok=True)
                
            logger.success(f"Successfully restored settings from backup: {backup_path}")
            return True
            
        except PermissionError as e:
            logger.error(f"Permission denied restoring backup: {str(e)}")
        except Exception as e:
            logger.error(f"Error restoring backup: {str(e)}")
        return False 