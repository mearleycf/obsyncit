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

from obsyncit.errors import BackupError, handle_file_operation_error


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

    def create_backup(self) -> Path | None:
        """Create a backup of the current settings.

        Returns:
            Path | None: Path to the created backup, or None if no settings to backup

        Raises:
            BackupError: If backup creation fails
        """
        try:
            # Create backup directory if it doesn't exist
            self.backup_dir.mkdir(exist_ok=True)

            # Check if there are settings to backup
            if not self.settings_dir.exists() or not any(self.settings_dir.iterdir()):
                logger.info("No settings to backup - skipping backup creation")
                return None

            # Create timestamped backup directory with microseconds for uniqueness
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backup_path = self.backup_dir / f"backup_{timestamp}"
            backup_path.mkdir(exist_ok=True)

            # Copy settings to backup
            backup_settings_dir = backup_path / ".obsidian"
            shutil.copytree(self.settings_dir, backup_settings_dir)

            # Clean up old backups
            self._cleanup_old_backups()

            logger.info(f"Created backup at {backup_path}")
            return backup_path

        except Exception as e:
            raise BackupError(f"Failed to create backup: {str(e)}", backup_path=self.settings_dir) from e

    def restore_backup(self, backup_path: Optional[Path] = None) -> Path:
        """Restore settings from a backup.

        Args:
            backup_path: Optional specific backup to restore from

        Returns:
            Path: Path to the restored backup

        Raises:
            BackupError: If restore fails or backup not found
        """
        try:
            # Get backup to restore
            backup_to_restore = self._get_backup_path(backup_path)
            if not backup_to_restore:
                raise BackupError("No backup found to restore", backup_path=backup_path)

            # Verify backup contains settings
            backup_settings = backup_to_restore / ".obsidian"
            if not backup_settings.exists():
                raise BackupError("Invalid backup - no settings found", backup_path=backup_to_restore)

            # Create backup of current settings before restore
            if self.settings_dir.exists():
                self.create_backup()

            # Remove current settings directory
            if self.settings_dir.exists():
                shutil.rmtree(self.settings_dir)

            # Copy backup settings to vault
            shutil.copytree(backup_settings, self.settings_dir)
            logger.info(f"Restored settings from: {backup_to_restore}")
            return backup_to_restore

        except Exception as e:
            if isinstance(e, BackupError):
                raise
            handle_file_operation_error(e, "restoring backup", self.settings_dir)
            raise BackupError("Failed to restore backup", backup_path=backup_path) from e

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
            backups = [Path(p) for p in self.list_backups()]
            if len(backups) > self.max_backups:
                for old_backup in backups[self.max_backups:]:
                    try:
                        if old_backup.exists():
                            shutil.rmtree(old_backup)
                            logger.debug(f"Removed old backup: {old_backup}")
                    except Exception as e:
                        handle_file_operation_error(e, "removing old backup", old_backup)

        except Exception as e:
            handle_file_operation_error(e, "cleaning up backups", self.backup_dir)
