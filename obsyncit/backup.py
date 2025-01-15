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
            PermissionError: If unable to access required directories
            FileNotFoundError: If required files are missing
            OSError: If there are OS-level issues
        """
        try:
            # Create backup directory if it doesn't exist
            try:
                self.backup_dir.mkdir(exist_ok=True)
            except PermissionError as e:
                raise BackupError(
                    "Permission denied creating backup directory",
                    backup_path=self.backup_dir,
                    details=str(e)
                ) from e
            except OSError as e:
                raise BackupError(
                    "Failed to create backup directory",
                    backup_path=self.backup_dir,
                    details=str(e)
                ) from e

            # Check if there are settings to backup
            if not self.settings_dir.exists() or not any(self.settings_dir.iterdir()):
                logger.info("No settings to backup - skipping backup creation")
                return None

            # Create timestamped backup directory with microseconds for uniqueness
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backup_path = self.backup_dir / f"backup_{timestamp}"
            try:
                backup_path.mkdir(exist_ok=True)
            except PermissionError as e:
                raise BackupError(
                    "Permission denied creating backup",
                    backup_path=backup_path,
                    details=str(e)
                ) from e
            except OSError as e:
                raise BackupError(
                    "Failed to create backup",
                    backup_path=backup_path,
                    details=str(e)
                ) from e

            # Copy settings to backup
            backup_settings_dir = backup_path / ".obsidian"
            try:
                shutil.copytree(self.settings_dir, backup_settings_dir)
            except PermissionError as e:
                raise BackupError(
                    "Permission denied copying settings",
                    backup_path=backup_path,
                    details=str(e)
                ) from e
            except FileNotFoundError as e:
                raise BackupError(
                    "Settings directory not found",
                    backup_path=backup_path,
                    details=str(e)
                ) from e
            except OSError as e:
                raise BackupError(
                    "Failed to copy settings",
                    backup_path=backup_path,
                    details=str(e)
                ) from e

            # Clean up old backups
            self._cleanup_old_backups()

            logger.info(f"Created backup at {backup_path}")
            return backup_path

        except (PermissionError, FileNotFoundError, OSError) as e:
            # These should already be wrapped in BackupError by the specific handlers
            raise
        except Exception as e:
            # Handle any unexpected errors
            raise BackupError(
                "Unexpected error during backup",
                backup_path=self.backup_dir,
                details=f"Error type: {type(e).__name__}, Message: {str(e)}"
            ) from e

    def restore_backup(self, backup_path: Optional[Path] = None) -> Path:
        """Restore settings from a backup.

        Args:
            backup_path: Optional specific backup to restore from

        Returns:
            Path: Path to the restored backup

        Raises:
            BackupError: If restore fails or backup not found
            PermissionError: If unable to access required directories
            FileNotFoundError: If required files are missing
            OSError: If there are OS-level issues
        """
        try:
            # Get backup to restore
            backup_to_restore = self._get_backup_path(backup_path)
            if not backup_to_restore:
                raise BackupError(
                    "No backup found to restore",
                    backup_path=backup_path,
                    details="Backup path not found or no backups available"
                )

            # Verify backup contains settings
            backup_settings = backup_to_restore / ".obsidian"
            if not backup_settings.exists():
                raise BackupError(
                    "Invalid backup - no settings found",
                    backup_path=backup_to_restore,
                    details="Backup directory does not contain .obsidian settings"
                )

            # Create backup of current settings before restore
            if self.settings_dir.exists():
                self.create_backup()

            # Remove current settings directory
            if self.settings_dir.exists():
                try:
                    shutil.rmtree(self.settings_dir)
                except PermissionError as e:
                    raise BackupError(
                        "Permission denied removing current settings",
                        backup_path=backup_to_restore,
                        details=str(e)
                    ) from e
                except OSError as e:
                    raise BackupError(
                        "Failed to remove current settings",
                        backup_path=backup_to_restore,
                        details=str(e)
                    ) from e

            # Copy backup settings to vault
            try:
                shutil.copytree(backup_settings, self.settings_dir)
            except PermissionError as e:
                raise BackupError(
                    "Permission denied restoring settings",
                    backup_path=backup_to_restore,
                    details=str(e)
                ) from e
            except FileNotFoundError as e:
                raise BackupError(
                    "Backup settings not found",
                    backup_path=backup_to_restore,
                    details=str(e)
                ) from e
            except OSError as e:
                raise BackupError(
                    "Failed to restore settings",
                    backup_path=backup_to_restore,
                    details=str(e)
                ) from e

            logger.info(f"Restored settings from: {backup_to_restore}")
            return backup_to_restore

        except BackupError:
            raise
        except (PermissionError, FileNotFoundError, OSError) as e:
            raise BackupError(
                "System error during restore",
                backup_path=backup_path,
                details=f"Error type: {type(e).__name__}, Message: {str(e)}"
            ) from e
        except Exception as e:
            raise BackupError(
                "Unexpected error during restore",
                backup_path=backup_path,
                details=f"Error type: {type(e).__name__}, Message: {str(e)}"
            ) from e

    def list_backups(self) -> List[str]:
        """List available backups.

        Returns:
            List[str]: List of backup paths

        Note:
            This method handles errors internally and returns an empty list on failure
            to maintain compatibility with existing code that expects a list.
        """
        try:
            if not self.backup_dir.exists():
                return []

            try:
                backups = sorted(
                    [str(p) for p in self.backup_dir.glob("backup_*")],
                    reverse=True
                )
                return backups
            except PermissionError as e:
                logger.error(f"Permission denied listing backups: {str(e)}")
                return []
            except OSError as e:
                logger.error(f"Error listing backups: {str(e)}")
                return []

        except Exception as e:
            logger.error(f"Unexpected error listing backups: {str(e)}")
            return []

    def _get_backup_path(self, backup_path: Optional[Path] = None) -> Optional[Path]:
        """Get the path of the backup to restore.

        Args:
            backup_path: Optional specific backup to restore from

        Returns:
            Optional[Path]: Path to the backup, or None if not found

        Note:
            This method handles errors internally and returns None on failure
            to maintain compatibility with existing code that expects an optional path.
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
            logger.error(f"Error getting backup path: {str(e)}")
            return None

    def _cleanup_old_backups(self) -> None:
        """Remove old backups exceeding the maximum count.

        Note:
            This method handles errors internally to prevent backup creation from failing
            due to cleanup issues.
        """
        try:
            backups = [Path(p) for p in self.list_backups()]
            if len(backups) > self.max_backups:
                for old_backup in backups[self.max_backups:]:
                    try:
                        if old_backup.exists():
                            shutil.rmtree(old_backup)
                            logger.debug(f"Removed old backup: {old_backup}")
                    except PermissionError as e:
                        logger.warning(f"Permission denied removing old backup {old_backup}: {str(e)}")
                    except OSError as e:
                        logger.warning(f"Error removing old backup {old_backup}: {str(e)}")

        except Exception as e:
            logger.warning(f"Error during backup cleanup: {str(e)}")
