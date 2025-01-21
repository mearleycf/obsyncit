"""Backup Management for Obsidian Settings.

This module provides comprehensive backup functionality for Obsidian vault
settings, including creation, restoration, and management of backups.
It handles:

1. Backup Creation
   - Automatic backup before sync operations
   - Verification of backup integrity
   - Rotation of old backups

2. Backup Restoration
   - Complete settings restoration
   - Safety backup before restore
   - Verification after restore

3. Backup Management
   - Listing available backups
   - Cleanup of old backups
   - Backup information tracking

Example Usage:
    >>> from pathlib import Path
    >>> from obsyncit.backup import BackupManager
    >>> 
    >>> # Initialize backup manager
    >>> backup_mgr = BackupManager(
    ...     vault_path=Path("/path/to/vault"),
    ...     backup_dir=Path(".backups"),
    ...     max_backups=5
    ... )
    >>> 
    >>> # Create a backup
    >>> backup_info = backup_mgr.create_backup()
    >>> print(f"Created backup at: {backup_info.path}")
    >>> print(f"Settings backed up: {backup_info.settings_count}")
    >>> 
    >>> # List available backups
    >>> backups = backup_mgr.list_backups()
    >>> for backup in backups:
    ...     print(f"{backup.timestamp}: {backup.size_mb:.1f}MB")
    >>> 
    >>> # Restore from backup
    >>> restored = backup_mgr.restore_backup()
    >>> if restored:
    ...     print(f"Restored from: {restored.timestamp}")
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Sequence, Union

from loguru import logger

from obsyncit.errors import BackupError


@dataclass
class BackupInfo:
    """Information about a backup.
    
    This immutable dataclass stores metadata about a backup, including
    its location, contents, and creation time.
    
    Attributes:
        path: Full path to the backup directory
        timestamp: Unix timestamp of backup creation
        settings_count: Number of settings files backed up
        has_plugins: Whether plugin data was backed up
        has_themes: Whether themes were backed up
        has_icons: Whether plugin icons were backed up
        size_mb: Size of the backup in megabytes
    
    Example:
        >>> info = BackupInfo.from_backup_path(Path("backups/backup_123456"))
        >>> print(f"Created: {datetime.fromtimestamp(info.timestamp)}")
        >>> print(f"Settings: {info.settings_count}")
        >>> print(f"Size: {info.size_mb:.1f}MB")
        >>> if info.has_plugins:
        ...     print("Includes plugin data")
    """
    
    path: Path
    timestamp: float
    settings_count: int
    has_plugins: bool = False
    has_themes: bool = False
    has_icons: bool = False
    size_mb: float = 0.0

    @classmethod
    def from_backup_path(cls, backup_path: Path) -> BackupInfo:
        """Create BackupInfo from a backup directory.
        
        This factory method analyzes a backup directory to create
        a BackupInfo object with metadata about the backup.
        
        Args:
            backup_path: Path to the backup directory
        
        Returns:
            BackupInfo object with backup metadata
            
        Raises:
            ValueError: If backup_path is not a valid backup
        
        Example:
            >>> path = Path("backups/backup_123456")
            >>> if info := BackupInfo.from_backup_path(path):
            ...     print(f"Valid backup of {info.size_mb:.1f}MB")
            ... else:
            ...     print("Invalid backup directory")
        """
        if not backup_path.exists():
            raise ValueError(f"Backup not found: {backup_path}")
            
        settings_dir = backup_path / ".obsidian"
        if not settings_dir.exists():
            raise ValueError(f"No settings found in backup: {backup_path}")
            
        # Get backup timestamp from directory name
        try:
            timestamp = float(backup_path.name.split("_")[1])
        except (IndexError, ValueError):
            timestamp = backup_path.stat().st_mtime
            
        # Count settings files
        settings_count = len(list(settings_dir.glob("*.json")))
        
        # Check for special directories
        has_plugins = (settings_dir / "plugins").exists()
        has_themes = (settings_dir / "themes").exists()
        has_icons = (settings_dir / "icons").exists()
        
        # Calculate total size
        total_size = sum(
            f.stat().st_size
            for f in backup_path.rglob("*")
            if f.is_file()
        )
        size_mb = total_size / (1024 * 1024)  # Convert to MB
        
        return cls(
            path=backup_path,
            timestamp=timestamp,
            settings_count=settings_count,
            has_plugins=has_plugins,
            has_themes=has_themes,
            has_icons=has_icons,
            size_mb=size_mb
        )

    def __str__(self) -> str:
        """Get a human-readable summary of the backup.
        
        Returns:
            Multi-line string with backup information
            
        Example:
            >>> info = BackupInfo.from_backup_path(path)
            >>> print(str(info))
            Backup from: 2024-01-18 12:34:56
            Location: /path/to/backup
            Settings: 12 files (1.5MB)
            Contents: plugins, themes, icons
        """
        timestamp = datetime.fromtimestamp(self.timestamp)
        contents = []
        if self.has_plugins:
            contents.append("plugins")
        if self.has_themes:
            contents.append("themes")
        if self.has_icons:
            contents.append("icons")
            
        return "\n".join([
            f"Backup from: {timestamp}",
            f"Location: {self.path}",
            f"Settings: {self.settings_count} files ({self.size_mb:.1f}MB)",
            f"Contents: {', '.join(contents) if contents else 'settings only'}"
        ])


class BackupManager:
    """Manages backups of Obsidian vault settings.
    
    This class provides comprehensive backup functionality for Obsidian
    vault settings, including creation, restoration, and management of
    backups. It ensures safe sync operations by maintaining backups
    of settings before modifications.
    
    The manager handles:
    - Automatic backup creation
    - Backup integrity verification
    - Safe restoration of backups
    - Rotation of old backups
    - Backup metadata tracking
    
    Attributes:
        vault_path: Path to the Obsidian vault
        settings_dir: Path to the .obsidian settings directory
        backup_dir: Path where backups are stored
        max_backups: Maximum number of backups to keep
    
    Important Files:
        The following files and directories are backed up:
        - Core settings (app.json, appearance.json, etc.)
        - Plugin settings and data
        - Theme files and CSS snippets
        - Plugin icons and resources
    
    Example:
        >>> # Initialize manager
        >>> backup_mgr = BackupManager(
        ...     vault_path="/path/to/vault",
        ...     backup_dir=".backups",
        ...     max_backups=5
        ... )
        >>> 
        >>> # Create backup
        >>> info = backup_mgr.create_backup()
        >>> print(f"Backup created: {info.path}")
        >>> 
        >>> # List backups
        >>> for backup in backup_mgr.list_backups():
        ...     print(f"{backup.timestamp}: {backup.size_mb:.1f}MB")
        >>> 
        >>> # Restore backup
        >>> if backup_mgr.restore_backup():
        ...     print("Backup restored successfully")
    """
    
    # Core settings files that must be backed up
    CORE_SETTINGS = {
        "app.json",
        "appearance.json",
        "hotkeys.json",
        "types.json",
        "templates.json",
    }
    
    # Plugin configuration files
    PLUGIN_SETTINGS = {
        "core-plugins.json",
        "community-plugins.json",
        "core-plugins-migration.json",
    }
    
    # Resource directories
    RESOURCE_DIRS = {
        "plugins",
        "themes",
        "snippets",
        "icons",
    }

    def __init__(
        self,
        vault_path: Union[str, Path],
        backup_dir: Optional[Union[str, Path]] = None,
        max_backups: int = 5,
    ) -> None:
        """Initialize the backup manager.
        
        Args:
            vault_path: Path to the Obsidian vault
            backup_dir: Optional custom backup directory path.
                       If not provided, uses .obsyncit/backups in vault.
            max_backups: Maximum number of backups to keep (default: 5)
        
        Raises:
            ValueError: If max_backups is less than 1
        
        Example:
            >>> # Basic initialization
            >>> mgr = BackupManager("/path/to/vault")
            >>> 
            >>> # Custom backup location and limit
            >>> mgr = BackupManager(
            ...     vault_path="/path/to/vault",
            ...     backup_dir="/path/to/backups",
            ...     max_backups=10
            ... )
        """
        if max_backups < 1:
            raise ValueError("max_backups must be at least 1")
            
        self.vault_path = Path(vault_path).resolve()
        self.settings_dir = self.vault_path / ".obsidian"
        
        # Use custom backup dir or default to .obsyncit/backups in vault
        if backup_dir:
            self.backup_dir = Path(backup_dir).resolve()
        else:
            self.backup_dir = self.vault_path / ".obsyncit" / "backups"
            
        self.max_backups = max_backups

    def create_backup(self) -> BackupInfo:
        """Create a backup of the vault settings.
        
        This method creates a complete backup of the vault's settings:
        1. Creates a timestamped backup directory
        2. Copies all settings files and directories
        3. Verifies backup integrity
        4. Cleans up old backups if needed
        
        Returns:
            BackupInfo object with metadata about the backup
            
        Raises:
            BackupError: If backup creation or verification fails
        
        Example:
            >>> # Create backup and check contents
            >>> info = backup_mgr.create_backup()
            >>> print(f"Created: {datetime.fromtimestamp(info.timestamp)}")
            >>> print(f"Settings: {info.settings_count}")
            >>> if info.has_plugins:
            ...     print("Plugins backed up")
        """
        try:
            # Create backup directory
            timestamp = int(time.time())
            backup_dir = self.backup_dir / f"backup_{timestamp}"
            backup_settings = backup_dir / ".obsidian"
            
            # Ensure backup directory exists
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy settings directory
            try:
                shutil.copytree(
                    self.settings_dir,
                    backup_settings,
                    dirs_exist_ok=True
                )
            except Exception as e:
                logger.error(f"Failed to copy settings: {e}")
                raise BackupError(
                    "Failed to copy settings",
                    vault_path=self.vault_path,
                    backup_path=backup_dir,
                )
            
            # Verify backup
            try:
                self._verify_backup(backup_settings)
            except BackupError as e:
                # Clean up failed backup
                shutil.rmtree(backup_dir, ignore_errors=True)
                raise
            
            # Get backup info
            try:
                backup_info = BackupInfo.from_backup_path(backup_dir)
            except ValueError as e:
                logger.error(f"Failed to get backup info: {e}")
                raise BackupError(
                    "Failed to create backup info",
                    backup_path=backup_dir,
                )
            
            # Clean up old backups
            self._cleanup_old_backups()
            
            logger.info(f"Created backup:\n{backup_info}")
            return backup_info
            
        except Exception as e:
            if isinstance(e, BackupError):
                raise
            raise BackupError(
                "Failed to create backup",
                vault_path=self.vault_path,
            ) from e

    def _verify_backup(self, backup_dir: Path) -> None:
        """Verify backup integrity.
        
        This method performs comprehensive verification of a backup:
        1. Checks all core settings files were backed up
        2. Verifies plugin settings and data
        3. Confirms resource directories were copied
        
        Args:
            backup_dir: Path to the backup's .obsidian directory
            
        Raises:
            BackupError: If any required files or directories are missing
        
        Example:
            >>> backup_dir = Path("backups/backup_123456/.obsidian")
            >>> try:
            ...     backup_mgr._verify_backup(backup_dir)
            ...     print("Backup verified successfully")
            ... except BackupError as e:
            ...     print(f"Verification failed: {e}")
            ...     if e.details:
            ...         print(f"Missing: {e.details}")
        """
        # Check core settings
        missing_settings = [
            f for f in self.CORE_SETTINGS
            if (self.settings_dir / f).exists()
            and not (backup_dir / f).exists()
        ]
        if missing_settings:
            raise BackupError(
                "Missing core settings in backup",
                backup_path=backup_dir,
                details=f"Missing: {', '.join(missing_settings)}"
            )
            
        # Check plugin files
        missing_plugins = [
            f for f in self.PLUGIN_SETTINGS
            if (self.settings_dir / f).exists()
            and not (backup_dir / f).exists()
        ]
        if missing_plugins:
            raise BackupError(
                "Missing plugin settings in backup",
                backup_path=backup_dir,
                details=f"Missing: {', '.join(missing_plugins)}"
            )
            
        # Check resource directories
        missing_dirs = [
            d for d in self.RESOURCE_DIRS
            if (self.settings_dir / d).exists()
            and not (backup_dir / d).exists()
        ]
        if missing_dirs:
            raise BackupError(
                "Missing resource directories in backup",
                backup_path=backup_dir,
                details=f"Missing: {', '.join(missing_dirs)}"
            )

    def restore_backup(
        self, backup_path: Optional[Path | str] = None
    ) -> BackupInfo:
        """Restore settings from a backup.

        This method performs a complete restoration of settings:
        1. Validates the backup integrity
        2. Creates safety backup of current settings
        3. Restores all settings files
        4. Restores plugins and their data
        5. Restores themes and snippets
        6. Restores plugin icons and resources

        Args:
            backup_path: Optional specific backup to restore from.
                       If None, uses most recent backup.

        Returns:
            BackupInfo object for the restored backup

        Raises:
            BackupError: If restore fails or backup not found
            
        Example:
            >>> # Restore most recent backup
            >>> if info := backup_mgr.restore_backup():
            ...     print(f"Restored from: {info.timestamp}")
            ...     print(f"Settings: {info.settings_count}")
            >>> 
            >>> # Restore specific backup
            >>> path = Path("backups/backup_123456")
            >>> if info := backup_mgr.restore_backup(path):
            ...     print(f"Restored backup from {path}")
        """
        try:
            # Get backup to restore
            backup_to_restore = self._get_backup_path(backup_path)
            if not backup_to_restore:
                raise BackupError(
                    "No backup found to restore",
                    backup_path=backup_path or self.backup_dir,
                )

            # Get backup info
            try:
                backup_info = BackupInfo.from_backup_path(backup_to_restore)
            except Exception as e:
                logger.error(f"Failed to get backup info: {e}")
                raise BackupError("Invalid backup format", backup_path=backup_to_restore)

            # Verify backup structure
            backup_settings = backup_to_restore / ".obsidian"
            if not backup_settings.exists():
                raise BackupError(
                    "Invalid backup - no settings found",
                    backup_path=backup_to_restore,
                )

            # Create safety backup
            if self.settings_dir.exists():
                try:
                    self.create_backup()
                except Exception as e:
                    logger.warning(f"Failed to backup current settings before restore: {e}")
                    # Continue with restore

            # Prepare for restore
            if self.settings_dir.exists():
                try:
                    shutil.rmtree(self.settings_dir)
                except Exception as e:
                    logger.error(f"Failed to remove existing settings: {e}")
                    raise BackupError(
                        "Failed to prepare for restore", 
                        backup_path=backup_to_restore
                    )

            # Perform restore
            try:
                # Restore all settings
                shutil.copytree(backup_settings, self.settings_dir)
                
                # Verify critical files were restored
                self._verify_backup(self.settings_dir)
                
            except Exception as e:
                logger.error(f"Failed to restore settings: {e}")
                # Try to recreate empty settings directory
                try:
                    if not self.settings_dir.exists():
                        self.settings_dir.mkdir(parents=True)
                except Exception:
                    pass  # Ignore recreation errors
                raise BackupError(
                    "Failed to restore backup", 
                    backup_path=backup_to_restore
                )

            logger.info(f"Restored settings from backup:\n{backup_info}")
            return backup_info

        except Exception as e:
            if isinstance(e, BackupError):
                raise
            raise BackupError(
                "Failed to restore backup",
                backup_path=backup_path or self.backup_dir,
            ) from e

    def list_backups(self) -> Sequence[BackupInfo]:
        """List available backups.

        Returns a list of all available backups, sorted by timestamp
        with the newest first. Each backup includes detailed information
        about its contents and size.

        Returns:
            List of BackupInfo objects, sorted newest to oldest
            
        Example:
            >>> # List all backups
            >>> backups = backup_mgr.list_backups()
            >>> for b in backups:
            ...     print(f"{datetime.fromtimestamp(b.timestamp)}")
            ...     print(f"  Settings: {b.settings_count}")
            ...     print(f"  Size: {b.size_mb:.1f}MB")
            ...     if b.has_plugins:
            ...         print("  Includes plugins")
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
            logger.error(f"Error listing backups: {e}")
            return []

    def _get_backup_path(self, backup_path: Optional[Path | str] = None) -> Optional[Path]:
        """Get the path of the backup to restore.
        
        This internal helper method resolves the backup path to use:
        1. If a specific path is provided, validates it exists
        2. Otherwise, finds the most recent valid backup
        3. Returns None if no valid backup is found
        
        Args:
            backup_path: Optional specific backup to restore from
            
        Returns:
            Path to the backup if found, None otherwise
            
        Example:
            >>> # Get most recent backup
            >>> if path := backup_mgr._get_backup_path():
            ...     print(f"Found backup: {path}")
            >>> 
            >>> # Get specific backup
            >>> path = backup_mgr._get_backup_path("backups/backup_123456")
            >>> if path and path.exists():
            ...     print("Valid backup found")
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
            logger.error(f"Error getting backup path: {e}")
            return None

    def _cleanup_old_backups(self) -> None:
        """Remove old backups exceeding maximum count.
        
        This internal method maintains the backup directory by:
        1. Getting a list of all backups sorted by age
        2. Keeping the newest max_backups backups
        3. Safely removing any older backups
        4. Logging cleanup activities
        
        Note:
            This is called automatically after creating new backups.
            Errors during cleanup are logged but don't stop backup
            creation.
            
        Example:
            >>> # Clean up old backups
            >>> backup_mgr._cleanup_old_backups()
            >>> 
            >>> # Verify backup count
            >>> backups = backup_mgr.list_backups()
            >>> assert len(backups) <= backup_mgr.max_backups
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
                        logger.warning(f"Failed to remove old backup: {e}")
        except Exception as e:
            logger.error(f"Error during backup cleanup: {e}")
            # Don't raise - cleanup failure shouldn't stop backup creation