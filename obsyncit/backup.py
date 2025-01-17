"""
Backup Manager - Handles backup operations for Obsidian vaults.

This module provides functionality for creating, managing, and restoring backups
of Obsidian vault settings. It handles timestamped backups, rotation of old backups,
and restoration from backups.

Typical usage example:
    >>> from pathlib import Path
    >>> from obsyncit.backup import BackupManager
    >>> 
    >>> # Initialize backup manager
    >>> backup_mgr = BackupManager(
    ...     vault_path=Path("~/vaults/my_vault"),
    ...     backup_dir=".backups",
    ...     max_backups=5
    ... )
    >>> 
    >>> # Create a backup
    >>> backup_path = backup_mgr.create_backup()
    >>> 
    >>> # List available backups
    >>> backups = backup_mgr.list_backups()
    >>> 
    >>> # Restore from latest backup
    >>> backup_mgr.restore_backup()
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence

from loguru import logger

from obsyncit.errors import BackupError


@dataclass
class BackupInfo:
    """Information about a backup.
    
    Attributes:
        path: Path to the backup directory
        timestamp: Timestamp when the backup was created
        size_bytes: Total size of the backup in bytes
        settings_count: Number of settings files in the backup
    """
    path: Path
    timestamp: datetime
    size_bytes: int
    settings_count: int

    def __lt__(self, other: 'BackupInfo') -> bool:
        """Compare backups by timestamp."""
        return self.timestamp < other.timestamp

    def __eq__(self, other: object) -> bool:
        """Compare backups for equality."""
        if not isinstance(other, BackupInfo):
            return NotImplemented
        return self.timestamp == other.timestamp

    @classmethod
    def from_backup_path(cls, backup_path: Path) -> 'BackupInfo':
        """Create a BackupInfo instance from a backup directory path.
        
        Args:
            backup_path: Path to the backup directory

        Returns:
            BackupInfo for the given backup

        Raises:
            ValueError: If the backup path is invalid or malformed
        """
        # Extract timestamp from directory name
        try:
            timestamp_str = backup_path.name.replace('backup_', '')
            timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S_%f')
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid backup path format: {backup_path}") from e

        # Calculate size and count settings
        try:
            settings_dir = backup_path / ".obsidian"
            size = sum(f.stat().st_size for f in settings_dir.rglob('*') if f.is_file())
            settings_count = sum(1 for _ in settings_dir.rglob('*.json'))
        except Exception:
            size = 0
            settings_count = 0

        return cls(
            path=backup_path,
            timestamp=timestamp,
            size_bytes=size,
            settings_count=settings_count
        )

    def __str__(self) -> str:
        """Get a human-readable representation of the backup info."""
        size_mb = self.size_bytes / (1024 * 1024)
        return (
            f"Backup from {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Path: {self.path}\n"
            f"Size: {size_mb:.2f} MB\n"
            f"Settings files: {self.settings_count}"
        )


class BackupManager:
    """Manages backups of Obsidian vault settings.
    
    This class handles creating, listing, and restoring backups of Obsidian vault
    settings. It supports automatic rotation of old backups and provides detailed
    information about available backups.

    Attributes:
        vault_path: Path to the Obsidian vault
        backup_dir: Directory where backups are stored
        max_backups: Maximum number of backups to keep
        settings_dir: Path to the vault's .obsidian directory
    """

    def __init__(
        self,
        vault_path: Path | str,
        backup_dir: str = ".backups",
        max_backups: int = 5,
    ) -> None:
        """Initialize the backup manager.

        Args:
            vault_path: Path to the Obsidian vault
            backup_dir: Directory to store backups in (relative to vault_path)
            max_backups: Maximum number of backups to keep

        Raises:
            ValueError: If max_backups is less than 1
        """
        if max_backups < 1:
            raise ValueError("max_backups must be at least 1")

        self.vault_path = Path(vault_path)
        self.backup_dir = self.vault_path / backup_dir
        self.max_backups = max_backups
        self.settings_dir = self.vault_path / ".obsidian"

    def create_backup(self) -> Optional[BackupInfo]:
        """Create a backup of the current settings.

        Creates a timestamped backup of the vault's settings directory.
        If there are no settings to back up, returns None.
        Automatically rotates old backups based on max_backups setting.

        Returns:
            BackupInfo for the created backup, or None if no settings to backup

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

            # Create timestamped backup directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backup_path = self.backup_dir / f"backup_{timestamp}"
            backup_path.mkdir(exist_ok=True)

            # Copy settings to backup
            backup_settings_dir = backup_path / ".obsidian"
            shutil.copytree(self.settings_dir, backup_settings_dir)

            # Clean up old backups
            self._cleanup_old_backups()

            # Create and log backup info
            backup_info = BackupInfo.from_backup_path(backup_path)
            logger.info(f"Created backup:\n{backup_info}")
            return backup_info

        except Exception as e:
            raise BackupError(
                f"Failed to create backup: {str(e)}",
                backup_path=self.settings_dir,
            ) from e

    def restore_backup(
        self, backup_path: Optional[Path | str] = None
    ) -> BackupInfo:
        """Restore settings from a backup.

        If no specific backup_path is provided, restores from the most recent backup.
        Creates a backup of current settings before restoring.

        Args:
            backup_path: Optional specific backup to restore from

        Returns:
            BackupInfo for the restored backup

        Raises:
            BackupError: If restore fails or backup not found
        """
        try:
            # Get backup to restore
            backup_to_restore = self._get_backup_path(backup_path)
            if not backup_to_restore:
                raise BackupError(
                    "No backup found to restore",
                    backup_path=backup_path or self.backup_dir,
                )

            # Get backup info for logging
            backup_info = BackupInfo.from_backup_path(backup_to_restore)

            # Verify backup contains settings
            backup_settings = backup_to_restore / ".obsidian"
            if not backup_settings.exists():
                raise BackupError(
                    "Invalid backup - no settings found",
                    backup_path=backup_to_restore,
                )

            # Create backup of current settings before restore
            if self.settings_dir.exists():
                self.create_backup()

            # Remove current settings directory
            if self.settings_dir.exists():
                shutil.rmtree(self.settings_dir)

            # Copy backup settings to vault
            shutil.copytree(backup_settings, self.settings_dir)
            logger.info(f"Restored settings from backup:\n{backup_info}")
            return backup_info

        except Exception as e:
            if isinstance(e, BackupError):
                raise
            raise BackupError(
                f"Failed to restore backup: {str(e)}",
                backup_path=backup_path or self.backup_dir,
            ) from e

    def list_backups(self) -> Sequence[BackupInfo]:
        """List available backups.

        Returns:
            List of BackupInfo objects for all available backups,
            sorted by timestamp (newest first)
        """
        try:
            if not self.backup_dir.exists():
                return []

            backups = []
            for path in self.backup_dir.glob("backup_*"):
                try:
                    backup_info = BackupInfo.from_backup_path(path)
                    backups.append(backup_info)
                except ValueError:
                    logger.warning(f"Skipping invalid backup directory: {path}")
                    continue

            return sorted(
                backups,
                key=lambda x: x.timestamp,
                reverse=True,
            )

        except Exception as e:
            logger.error(f"Error listing backups: {str(e)}")
            return []

    def _get_backup_path(self, backup_path: Optional[Path | str] = None) -> Optional[Path]:
        """Get the path of the backup to restore.

        Args:
            backup_path: Optional specific backup to restore from

        Returns:
            Path to the backup, or None if not found
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

            return backups[0].path

        except Exception as e:
            logger.error(
                f"Error getting backup path: {str(e)}"
                f" (path: {backup_path or self.backup_dir})"
            )
            return None

    def _cleanup_old_backups(self) -> None:
        """Remove old backups exceeding the maximum count.
        
        This method removes the oldest backups when the total number
        of backups exceeds max_backups. Backup age is determined by
        the timestamp in the directory name.
        """
        try:
            backups = self.list_backups()
            if len(backups) > self.max_backups:
                for old_backup in backups[self.max_backups:]:
                    try:
                        if old_backup.path.exists():
                            shutil.rmtree(old_backup.path)
                            logger.debug(f"Removed old backup:\n{old_backup}")
                    except Exception as e:
                        logger.warning(
                            f"Error removing old backup {old_backup.path}: {str(e)}"
                        )

        except Exception as e:
            logger.error(f"Error cleaning up backups: {str(e)}")
