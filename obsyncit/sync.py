"""
Sync Manager - Core synchronization functionality.

This module provides the core functionality for syncing settings between Obsidian vaults.
It handles synchronization of various settings files and directories, backup management,
and validation of settings files.

Typical usage example:
    >>> from pathlib import Path
    >>> from obsyncit.sync import SyncManager
    >>> from obsyncit.schemas import Config
    >>>
    >>> # Initialize with source and target vaults
    >>> sync_mgr = SyncManager(
    ...     source_vault=Path("~/vaults/source"),
    ...     target_vault=Path("~/vaults/target"),
    ...     config=Config()
    ... )
    >>>
    >>> # Sync all settings
    >>> sync_mgr.sync_settings()
    >>>
    >>> # Or sync specific items
    >>> sync_mgr.sync_settings(items=["appearance.json", "themes"])
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Union, Dict, Any, Generator
from typing_extensions import Protocol
from contextlib import contextmanager

from loguru import logger

from obsyncit.backup import BackupManager
from obsyncit.errors import (
    BackupError,
    SyncError,
    ValidationError,
    ObsyncError,
)
from obsyncit.schemas import Config
from obsyncit.vault import VaultManager

class Validatable(Protocol):
    """Protocol for objects that can be validated."""
    def validate(self) -> bool:
        """Validate the object."""
        ...


@dataclass(frozen=True)
class SyncResult:
    """Result of a sync operation.
    
    Attributes:
        success: Whether the overall operation was successful
        items_synced: List of items that were successfully synced
        items_failed: List of items that failed to sync
        errors: Dict mapping items to their error messages
    """
    success: bool
    items_synced: List[str]
    items_failed: List[str]
    errors: Dict[str, str]

    def __post_init__(self) -> None:
        """Validate the sync result."""
        if not self.items_failed and not self.success:  # was self.items.failed
            raise ValueError("Invalid state: no failed items but success is False")

    @property
    def any_success(self) -> bool:
        """Check if any items were successfully synced."""
        return bool(self.items_synced)
    
    @property
    def summary(self) -> str:
        """Get a formatted summary of the sync operation."""
        return str(self)

    def __str__(self) -> str:
        """Get a human-readable summary of the sync result."""
        parts = [
            f"Sync {'successful' if self.success else 'failed'}",
            f"Items synced: {len(self.items_synced)}",
        ]
        if self.items_failed:
            parts.append(f"Items failed: {len(self.items_failed)}")
            for item, error in self.errors.items():
                parts.append(f"  - {item}: {error}")
        return "\n".join(parts)


class SyncManager:
    """Manages the synchronization of settings between Obsidian vaults.
    
    This class handles the synchronization of various settings files and directories
    between Obsidian vaults, including core settings, plugins, themes, and snippets.
    It provides backup functionality and validation of settings files.

    Attributes:
        source: VaultManager for the source vault
        target: VaultManager for the target vault
        config: Configuration object
        backup_mgr: BackupManager for handling backups
    """

    # Core settings files that can be synced
    CORE_SETTINGS_FILES = {"app.json", "appearance.json", "hotkeys.json"}
    
    # Plugin configuration files
    PLUGIN_FILES = {"core-plugins.json", "community-plugins.json"}
    
    # Directories that can be synced
    SYNC_DIRECTORIES = {"snippets", "themes"}

    def __init__(
        self,
        source_vault: Union[str, Path],
        target_vault: Union[str, Path],
        config: Config,
    ) -> None:
        """Initialize the sync manager.

        Args:
            source_vault: Path to the source vault
            target_vault: Path to the target vault
            config: Configuration object containing sync settings
        """
        self.source = VaultManager(source_vault)
        self.target = VaultManager(target_vault)
        self.config = config
        self.backup_mgr = BackupManager(
            self.target.vault_path,
            config.backup.backup_dir,
            config.backup.max_backups,
        )

    def sync_settings(self, items: Optional[List[str]] = None) -> SyncResult:
        """Sync settings from source to target vault.

        This method handles the complete sync process, including:
        - Vault validation
        - Backup creation (if not in dry run mode)
        - File and directory synchronization
        - Error handling and reporting

        Args:
            items: Optional list of specific items to sync. If None, syncs all items
                  based on configuration.

        Returns:
            SyncResult containing the outcome of the sync operation

        Raises:
            SyncError: If there is an unrecoverable error during sync
            ValidationError: If JSON validation fails for any settings file
            BackupError: If backup creation fails and ignore_errors is False
        """
        result = SyncResult(
            success=True,
            items_synced=[],
            items_failed=[],
            errors={},
        )

        try:
            # Validate vaults
            self._validate_vaults()

            # Create backup if not in dry run mode
            if not self.config.sync.dry_run:
                self._create_backup()

            # Get list of items to sync
            sync_items = self._get_sync_items(items)
            if not sync_items:
                logger.warning("No items to sync")
                return result

            # Ensure target settings directory exists
            if not self.config.sync.dry_run:
                self.target.settings_dir.mkdir(exist_ok=True)

            # Sync each item
            for item in sync_items:
                try:
                    self._sync_item(item)
                    result.items_synced.append(item)
                except Exception as e:
                    result.items_failed.append(item)
                    result.errors[item] = str(e)
                    if not self.config.sync.ignore_errors:
                        raise

            # Update success status
            result.success = not result.items_failed or self.config.sync.ignore_errors
            return result

        except Exception as e:
            logger.error(f"Sync failed: {str(e)}")
            logger.debug("", exc_info=True)
            if isinstance(e, (SyncError, ValidationError, BackupError)):
                raise
            raise SyncError(str(e), source=self.source.vault_path, target=self.target.vault_path) from e

    def _validate_vaults(self) -> None:
        """Validate both source and target vaults.
        
        Raises:
            SyncError: If either vault is invalid or inaccessible
        """

        validation_errors: List[str] = []
        
        if not self.source.validate_vault():
            validation_errors.append("Invalid source vault")
        if not self.target.validate_vault():
            validation_errors.append("Invalid target vault")

        if validation_errors:
            raise SyncError(
                "; ".join(validation_errors),
                source=self.source.vault_path,
                target=self.target.vault_path,
            )

    def _create_backup(self) -> None:
        """Create a backup of the target vault's settings.
        
        Raises:
            BackupError: If backup fails and ignore_errors is False
        """
        try:
            self.backup_mgr.create_backup()
        except BackupError as e:
            if not self.config.sync.ignore_errors:
                raise
            logger.warning(f"Backup failed but continuing: {str(e)}")

    def _get_sync_items(self, items: Optional[List[str]] = None) -> Set[str]:
        """Get the list of items to sync based on config and user input.

        This method determines which items should be synced based on:
        1. Configuration settings (enabled/disabled features)
        2. Existence of items in source vault
        3. User-specified items list (if provided)

        Args:
            items: Optional list of specific items to sync

        Returns:
            Set of items to sync
        """
        sync_items: Set[str] = set()

        # Add core settings if enabled
        if self.config.sync.core_settings:
            sync_items.update(
                item for item in self.CORE_SETTINGS_FILES
                if (self.source.settings_dir / item).exists()
            )

        # Add plugin settings if enabled
        if self.config.sync.core_plugins or self.config.sync.community_plugins:
            sync_items.update(
                item for item in self.PLUGIN_FILES
                if (self.source.settings_dir / item).exists()
            )

        # Add directories if enabled
        if self.config.sync.snippets:
            if (self.source.settings_dir / "snippets").exists():
                sync_items.add("snippets")

        if self.config.sync.themes:
            if (self.source.settings_dir / "themes").exists():
                sync_items.add("themes")

        # Filter by user-specified items if provided
        if items:
            sync_items = {item for item in items if item in sync_items}

        return sync_items

    def validate_json_file(
        self,
        file_path: Path,
        required_fields: Optional[List[str]] = None,
        schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validate a JSON file against schema and required fields.
        
        Args:
            file_path: Path to the JSON file
            required_fields: Optional list of required field names
            schema: Optional JSON schema for validation
            
        Returns:
            Validated JSON data as a dictionary
            
        Raises:
            ValidationError: If validation fails
            ObsyncError: If file operations fail
        """
        if not file_path.exists():
            raise ObsyncError(f"File not found: {file_path}", str(file_path))
            
        try:
            data = json.loads(file_path.read_text())
        except (PermissionError, OSError) as e:
            raise ObsyncError(f"Failed to read file: {e}", str(file_path))
        except json.JSONDecodeError as e:
            raise ValidationError("Invalid JSON", file_path, [str(e)])
            
        if required_fields:
            missing = [f for f in required_fields if f not in data]
            if missing:
                raise ValidationError(
                    "Missing required fields",
                    file_path,
                    [f"Missing: {', '.join(missing)}"]
                )
                
        return data

    @contextmanager
    def _sync_operation(self, item: str) -> Generator[None, None, None]:
        """Context manager for sync operations with logging.
        
        Args:
            item: Name of the item to sync

        Yields:
            None
            
        Raises:
            SyncError: If there is an error during sync
        """
        logger.info(f"Starting sync of {item}")
        try:
            yield
        except Exception as e:
            logger.error(f"Failed to sync {item}: {e}")
            raise
        else:
            logger.info(f"Successfully synced {item}")

    def _sync_item(self, item: str) -> None:
        """Sync a specific settings item from source to target.

        This method handles both file and directory synchronization:
        - For JSON files, validates the content before copying
        - For directories, uses recursive copy with existing directory handling
        - Supports dry run mode for testing

        Args:
            item: Name of the item to sync

        Raises:
            SyncError: If there is an error during sync
            ValidationError: If JSON validation fails
        """
        source_path = self.source.settings_dir / item
        target_path = self.target.settings_dir / item

        if not source_path.exists():
            raise SyncError(
                f"Source item does not exist: {item}",
                source=self.source.vault_path,
                target=self.target.vault_path,
            )

        with self._sync_operation(item):
            try:
                # Validate JSON files
                if item.endswith('.json'):
                    self.validate_json_file(source_path)

                # Copy file or directory
                if not self.config.sync.dry_run:
                    if source_path.is_file():
                        shutil.copy2(source_path, target_path)
                    else:
                        shutil.copytree(source_path, target_path, dirs_exist_ok=True)
                else:
                    logger.info(f"Would sync: {item} (dry run)")

            except Exception as e:
                if isinstance(e, (SyncError, ValidationError)):
                    raise
                raise SyncError(
                    f"Failed to sync {item}: {str(e)}",
                    source=self.source.vault_path,
                    target=self.target.vault_path,
                ) from e

    def list_backups(self) -> List[str]:
        """List available backups for the target vault.

        Returns:
            List of backup paths, sorted by creation time (newest first)
        """
        return self.backup_mgr.list_backups()

    def restore_backup(self, backup_path: Optional[Path] = None) -> bool:
        """Restore settings from a backup.

        Args:
            backup_path: Optional specific backup to restore from.
                       If None, restores from the most recent backup.

        Returns:
            True if restore was successful

        Raises:
            BackupError: If the backup doesn't exist or can't be restored
        """
        try:
            if self.config.sync.dry_run:
                logger.info(
                    f"Would restore from backup: {backup_path or 'latest'} (dry run)"
                )
                return True

            return self.backup_mgr.restore_backup(backup_path)

        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            logger.debug("", exc_info=True)
            return False
        