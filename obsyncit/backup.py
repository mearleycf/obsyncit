"""
Backup Manager - Handles backup operations for Obsidian vaults.

This module provides functionality for creating, managing, and restoring backups
of Obsidian vault settings.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from loguru import logger

from obsyncit.errors import handle_file_operation_error


class BackupManager:
    """Manages backups of Obsidian vault settings."""

    def __init__(
        self,
        vault_path: Path,
        backup_dir: str = ".backups",
        max_backups: int = 5
    ) -> None:
        """Initialize the backup manager.

        Args:
            vault_path: Path to the Obsidian vault
            backup_dir: Directory to store backups in
            max_backups: Maximum number of backups to keep
        """
        self.vault_path = Path(vault_path)
        self.backup_dir = self.vault_path / backup_dir
        self.max_backups = max_backups
        self.settings_dir = self.vault_path / ".obsidian"

    def create_backup(self) -> bool:
        """Create a backup of the current settings.

        Returns:
            bool: True if backup was successful
        """
        try:
            # Create backup directory if it doesn't exist
            self.backup_dir.mkdir(exist_ok=True)

            # Generate backup path with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"backup_{timestamp}"

            # Copy settings directory to backup location
            if self.settings_dir.exists():
                shutil.copytree(self.settings_dir, backup_path)
                logger.info(f"Created backup at: {backup_path}")

                # Clean up old backups
                self._cleanup_old_backups()
                return True

            logger.warning("No settings directory found to backup")
            return False

        except Exception as e:
            handle_file_operation_error(e, "creating backup", self.settings_dir)
            return False

    def restore_backup(self, backup_path: Optional[Path] = None) -> bool:
        """Restore settings from a backup.

        Args:
            backup_path: Optional specific backup to restore from

        Returns:
            bool: True if restore was successful
        """
        try:
            # Get backup to restore
            backup_to_restore = self._get_backup_path(backup_path)
            if not backup_to_restore:
                logger.error("No backup found to restore")
                return False

            # Create backup of current settings before restore
            if self.settings_dir.exists():
                self.create_backup()

            # Remove current settings directory
            if self.settings_dir.exists():
                shutil.rmtree(self.settings_dir)

            # Copy backup to settings directory
            shutil.copytree(backup_to_restore, self.settings_dir)
            logger.info(f"Restored settings from: {backup_to_restore}")
            return True

        except Exception as e:
            handle_file_operation_error(e, "restoring backup", self.settings_dir)
            return False

    def list_backups(self) -> List[str]:
        """List available backups.

        Returns:
            List[str]: List of backup paths
        """
        try:
            if not self.backup_dir.exists():
                return []

            backups = sorted(
                [str(p) for p in self.backup_dir.glob("backup_*")],
                reverse=True
            )
            return backups

        except Exception as e:
            handle_file_operation_error(e, "listing backups", self.backup_dir)
            return []

    def _get_backup_path(self, backup_path: Optional[Path] = None) -> Optional[Path]:
        """Get the path of the backup to restore.

        Args:
            backup_path: Optional specific backup to restore from

        Returns:
            Optional[Path]: Path to the backup, or None if not found
        """
        try:
            if backup_path:
                # Use specified backup if it exists
                backup_path = Path(backup_path)
                if not backup_path.exists():
                    logger.error(f"Specified backup not found: {backup_path}")
                    return None
                return backup_path

            # Get latest backup
            backups = self.list_backups()
            if not backups:
                return None

            return Path(backups[0])

        except Exception as e:
            handle_file_operation_error(e, "getting backup path", backup_path or self.backup_dir)
            return None

    def _cleanup_old_backups(self) -> None:
        """Remove old backups exceeding the maximum count."""
        try:
            backups = self.list_backups()
            if len(backups) > self.max_backups:
                for old_backup in backups[self.max_backups:]:
                    try:
                        shutil.rmtree(old_backup)
                        logger.debug(f"Removed old backup: {old_backup}")
                    except Exception as e:
                        handle_file_operation_error(e, "removing old backup", old_backup)

        except Exception as e:
            handle_file_operation_error(e, "cleaning up backups", self.backup_dir)
